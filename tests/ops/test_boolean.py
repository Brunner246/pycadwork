"""Boolean / cutting ops against the FakeCadworkAdapter.

The two watch-points pinned here: cwapi3d's cutters-first (``hard``/``soft``)
argument order is flipped by the ops layer, and the plane distance sent to
cadwork is ``-plane.d()``.
"""

from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    Plane3D,
    Point3D,
    RectSection,
    Vector3D,
    ops,
)
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


# ---- union ----


def test_union_merges_into_surviving_element(fake_cadwork: FakeCadworkAdapter):
    a, b, c = _beam(), _beam(), _beam()
    merged = ops.union(a, b, c)
    assert [e.id for e in merged] == [a.id]
    assert fake_cadwork.state.solder_calls == [[a.id, b.id, c.id]]
    assert b.id not in fake_cadwork.state.elements


def test_union_requires_at_least_two_elements():
    with pytest.raises(ValueError):
        ops.union(_beam())


# ---- difference ----


def test_difference_passes_cutters_as_hard_elements(
    fake_cadwork: FakeCadworkAdapter,
):
    target, cutter = _beam(), _beam()
    pieces = ops.difference(target, cutter)
    assert pieces == []
    assert fake_cadwork.state.subtract_calls == [([cutter.id], [target.id], False)]


def test_difference_with_undo_sets_the_flag(fake_cadwork: FakeCadworkAdapter):
    target, cutter = _beam(), _beam()
    ops.difference([target], [cutter], undo=True)
    assert fake_cadwork.state.subtract_calls == [([cutter.id], [target.id], True)]


def test_difference_wraps_split_off_pieces(fake_cadwork: FakeCadworkAdapter):
    target, cutter = _beam(), _beam()
    piece = _beam()  # stands in for a split-off piece the kernel would create
    fake_cadwork.state.pending_subtract_pieces.append(piece.id)
    pieces = ops.difference(target, cutter)
    assert [p.id for p in pieces] == [piece.id]
    assert isinstance(pieces[0], Beam)


# ---- plane cuts ----


def test_cut_with_plane_sends_negated_d_as_distance(
    fake_cadwork: FakeCadworkAdapter,
):
    beam = _beam()
    plane = Plane3D.from_point_and_normal(Point3D(0, 0, 5), Vector3D.unit_z())
    assert ops.cut_with_plane(beam, plane) is True
    assert fake_cadwork.state.plane_cut_calls == [(beam.id, (0.0, 0.0, 1.0), 5.0)]


def test_element_cut_with_plane_delegates_to_ops(
    fake_cadwork: FakeCadworkAdapter,
):
    beam = _beam()
    assert beam.cut_with_plane(Plane3D.xy(5.0)) is True
    assert fake_cadwork.state.plane_cut_calls[0][0] == beam.id


def test_slice_with_plane_returns_new_wrapped_elements():
    beam = _beam()
    pieces = beam.slice_with_plane(Plane3D.xy())
    assert len(pieces) == 1
    assert isinstance(pieces[0], Beam)
    assert pieces[0].id != beam.id


# ---- input normalization ----


def test_single_element_arguments_are_accepted(fake_cadwork: FakeCadworkAdapter):
    beam = _beam()
    ops.split(beam)  # bare Element, not an iterable
    assert fake_cadwork.state.split_calls == [[beam.id]]


# ---- remaining cuts: arguments recorded verbatim ----


def test_split_records_ids(fake_cadwork: FakeCadworkAdapter):
    a, b = _beam(), _beam()
    ops.split([a, b])
    assert fake_cadwork.state.split_calls == [[a.id, b.id]]


def test_cut_with_miter_records_the_pair(fake_cadwork: FakeCadworkAdapter):
    a, b = _beam(), _beam()
    assert ops.cut_with_miter(a, b) is True
    assert fake_cadwork.state.miter_calls == [(a.id, b.id)]


def test_cut_with_overmeasure_passes_cutters_as_hard_elements(
    fake_cadwork: FakeCadworkAdapter,
):
    target, cutter = _beam(), _beam()
    ops.cut_with_overmeasure(target, cutter)
    assert fake_cadwork.state.overmeasure_calls == [([cutter.id], [target.id])]


def test_cut_with_processing_group_records_args(
    fake_cadwork: FakeCadworkAdapter,
):
    target, processing = _beam(), _beam()
    ops.cut_with_processing_group(target, processing)
    assert fake_cadwork.state.processing_group_calls == [(target.id, processing.id)]


def test_cut_cross_lap_forwards_geometry_and_bolt_params(
    fake_cadwork: FakeCadworkAdapter,
):
    a, b = _beam(), _beam()
    ops.cut_cross_lap(
        [a, b],
        depth=100.0,
        clearance_base=1.0,
        clearance_side=2.0,
        drilling_count=2,
        drilling_diameter=12.0,
        drilling_tolerance=0.5,
    )
    assert fake_cadwork.state.cross_lap_calls == [
        ([a.id, b.id], 100.0, 1.0, 2.0, 2, 12.0, 0.5)
    ]

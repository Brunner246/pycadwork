"""Cutting-body extraction and the restore-on-exit context manager."""

from __future__ import annotations

import pytest

from pycadwork import AxisPoints, Beam, Point3D, RectSection, ops
from pycadwork.ops import cutting_bodies, extract_cutting_bodies
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


# ---- extraction ----


def test_extraction_groups_bodies_per_source(fake_cadwork: FakeCadworkAdapter):
    a, b, c = _beam(), _beam(), _beam()
    state = fake_cadwork.state
    state.pending_cutting_bodies[a.id] = 2
    state.pending_cutting_bodies[b.id] = 1

    extraction = extract_cutting_bodies([a, b, c])

    # the caller's own instances are the keys, in extraction order
    assert extraction.sources == [a, b, c]
    assert len(extraction.by_source[a]) == 2
    assert len(extraction.by_source[b]) == 1
    assert extraction.by_source[c] == []  # no processes -> uniform empty list
    assert len(extraction.bodies) == 3
    # per-source grouping requires one adapter call per source
    assert state.keep_cutting_bodies_calls == [
        ([a.id], True),
        ([b.id], True),
        ([c.id], True),
    ]


def test_extraction_passes_cutting_elements_only_flag(
    fake_cadwork: FakeCadworkAdapter,
):
    a = _beam()
    extract_cutting_bodies(a, cutting_elements_only=False)
    assert fake_cadwork.state.keep_cutting_bodies_calls == [([a.id], False)]


# ---- context manager ----


def test_cutting_bodies_restores_on_exit(fake_cadwork: FakeCadworkAdapter):
    a, b = _beam(), _beam()
    state = fake_cadwork.state
    state.pending_cutting_bodies[a.id] = 1
    state.pending_cutting_bodies[b.id] = 2

    with cutting_bodies([a, b]) as extraction:
        body_ids = [body.id for body in extraction.bodies]

    # one re-subtract per source: bodies as cutters (hard), source as soft
    a_bodies = [body.id for body in extraction.by_source[a]]
    b_bodies = [body.id for body in extraction.by_source[b]]
    assert state.subtract_calls == [
        (a_bodies, [a.id], False),
        (b_bodies, [b.id], False),
    ]
    assert all(bid not in state.elements for bid in body_ids)
    assert a.id in state.elements
    assert b.id in state.elements


def test_cutting_bodies_restores_when_block_raises(
    fake_cadwork: FakeCadworkAdapter,
):
    a = _beam()
    state = fake_cadwork.state
    state.pending_cutting_bodies[a.id] = 1

    with pytest.raises(RuntimeError, match="boom"):
        with cutting_bodies(a) as extraction:
            raise RuntimeError("boom")

    body_id = extraction.by_source[a][0].id
    assert state.subtract_calls == [([body_id], [a.id], False)]
    assert body_id not in state.elements


def test_body_deleted_inside_block_is_tolerated(fake_cadwork: FakeCadworkAdapter):
    a = _beam()
    state = fake_cadwork.state
    state.pending_cutting_bodies[a.id] = 2

    with cutting_bodies(a) as extraction:
        first, second = extraction.by_source[a]
        first.delete()

    assert state.subtract_calls == [([second.id], [a.id], False)]
    assert second.id not in state.elements


def test_source_deleted_inside_block_skips_subtract_but_cleans_bodies(
    fake_cadwork: FakeCadworkAdapter,
):
    a = _beam()
    state = fake_cadwork.state
    state.pending_cutting_bodies[a.id] = 1

    with cutting_bodies(a) as extraction:
        a.delete()

    body_id = extraction.by_source[a][0].id
    assert state.subtract_calls == []
    assert body_id not in state.elements


# ---- plain process deletion ----


def test_delete_processes_and_end_types_record_ids(
    fake_cadwork: FakeCadworkAdapter,
):
    a, b = _beam(), _beam()
    ops.delete_processes([a, b])
    ops.delete_end_types(a)
    assert fake_cadwork.state.delete_processes_calls == [[a.id, b.id]]
    assert fake_cadwork.state.delete_end_types_calls == [[a.id]]

"""DisplayRefreshScope + suppressed_display + auto_recreate against FakeCadworkAdapter."""

from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    DisplayRefreshScope,
    Drilling,
    Point3D,
    RectSection,
    Segment,
    auto_recreate,
    suppressed_display,
)


def _make_beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


def _make_drilling() -> Drilling:
    return Drilling.create(10.0, Segment(Point3D(0, 0, 0), Point3D(0, 0, 100)))


def test_scope_disables_and_reenables_refresh(fake_cadwork):
    state = fake_cadwork.state
    with DisplayRefreshScope():
        assert state.display_refresh_disable_calls == 1
        assert state.display_refresh_enable_calls == 0
    assert state.display_refresh_disable_calls == 1
    assert state.display_refresh_enable_calls == 1
    assert state.recreate_calls == []


def test_scope_tracks_single_element_and_recreates_before_enable(fake_cadwork):
    state = fake_cadwork.state
    with DisplayRefreshScope() as scope:
        beam = _make_beam()
        scope.track(beam)
        assert state.recreate_calls == []
        assert state.display_refresh_enable_calls == 0

    assert state.recreate_calls == [[beam.id]]
    assert state.display_refresh_enable_calls == 1


def test_scope_tracks_iterable_of_elements(fake_cadwork):
    with DisplayRefreshScope() as scope:
        a, b = _make_beam(), _make_beam()
        scope.track([a, b])

    assert fake_cadwork.state.recreate_calls == [[a.id, b.id]]


def test_scope_track_returns_input(fake_cadwork):
    with DisplayRefreshScope() as scope:
        beam = _make_beam()
        assert scope.track(beam) is beam
        elements = [_make_beam(), _make_beam()]
        assert scope.track(elements) is elements


def test_recreate_after_tracks_single_element_return(fake_cadwork):
    with DisplayRefreshScope() as scope:
        result = scope.recreate_after(_make_beam)
    assert isinstance(result, Beam)
    assert fake_cadwork.state.recreate_calls == [[result.id]]


def test_recreate_after_tracks_list_return(fake_cadwork):
    def make_three() -> list[Beam]:
        return [_make_beam(), _make_beam(), _make_beam()]

    with DisplayRefreshScope() as scope:
        beams = scope.recreate_after(make_three)

    assert len(beams) == 3
    assert fake_cadwork.state.recreate_calls == [[b.id for b in beams]]


def test_recreate_after_with_mixed_returns_only_tracks_elements(fake_cadwork):
    def make_mixed() -> list:
        return [_make_beam(), "not an element", _make_drilling()]

    with DisplayRefreshScope() as scope:
        result = scope.recreate_after(make_mixed)

    beam, _, drill = result
    assert fake_cadwork.state.recreate_calls == [[beam.id, drill.id]]


def test_scope_reenables_refresh_on_exception(fake_cadwork):
    state = fake_cadwork.state
    with pytest.raises(RuntimeError, match="boom"):
        with DisplayRefreshScope() as scope:
            scope.track(_make_beam())
            raise RuntimeError("boom")

    assert state.display_refresh_enable_calls == 1
    # tracked elements are NOT recreated when the block raises — view stays
    # consistent with whatever state the abort left behind.
    assert state.recreate_calls == []


def test_scope_works_as_function_decorator(fake_cadwork):
    scope = DisplayRefreshScope()

    @scope
    def build() -> Beam:
        beam = _make_beam()
        scope.track(beam)
        return beam

    beam = build()
    state = fake_cadwork.state
    assert state.display_refresh_disable_calls == 1
    assert state.display_refresh_enable_calls == 1
    assert state.recreate_calls == [[beam.id]]


def test_auto_recreate_decorator(fake_cadwork):
    @auto_recreate
    def make_one() -> Beam:
        return _make_beam()

    beam = make_one()
    state = fake_cadwork.state
    assert state.display_refresh_disable_calls == 1
    assert state.display_refresh_enable_calls == 1
    assert state.recreate_calls == [[beam.id]]


def test_auto_recreate_passes_through_args(fake_cadwork):
    @auto_recreate
    def make_drillings(count: int, *, diameter: float) -> list[Drilling]:
        return [
            Drilling.create(diameter, Segment(Point3D(i, 0, 0), Point3D(i, 0, 100)))
            for i in range(count)
        ]

    drills = make_drillings(3, diameter=8.0)
    assert len(drills) == 3
    assert fake_cadwork.state.recreate_calls == [[d.id for d in drills]]


def test_suppressed_display_disables_without_recreate(fake_cadwork):
    @suppressed_display
    def relabel(b: Beam) -> None:
        b.attrs.name = "Stud"

    beam = _make_beam()
    relabel(beam)

    state = fake_cadwork.state
    assert state.display_refresh_disable_calls == 1
    assert state.display_refresh_enable_calls == 1
    assert state.recreate_calls == []
    assert beam.attrs.name == "Stud"


def test_suppressed_display_reenables_on_exception(fake_cadwork):
    @suppressed_display
    def boom() -> None:
        raise ValueError("nope")

    with pytest.raises(ValueError, match="nope"):
        boom()

    assert fake_cadwork.state.display_refresh_enable_calls == 1

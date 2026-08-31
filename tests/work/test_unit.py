"""WorkUnit against FakeCadworkAdapter — commit, rollback, undo, report, track."""

from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    Point3D,
    RectSection,
    WorkStatus,
    WorkUnit,
)


def _make_beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


def test_apply_persists_and_commits(fake_cadwork):
    beams = [_make_beam(), _make_beam()]
    with WorkUnit(beams) as work:
        work.apply(name="Stud")

    for beam in beams:
        assert beam.attrs.name == "Stud"
    assert work.report.status is WorkStatus.COMMITTED
    assert fake_cadwork.state.recreate_calls == [[beams[0].id, beams[1].id]]


def test_exception_after_apply_restores_and_rolls_back(fake_cadwork):
    beams = [_make_beam(), _make_beam()]
    for beam in beams:
        beam.attrs.name = "Original"

    with pytest.raises(RuntimeError, match="boom"):
        with WorkUnit(beams) as work:
            work.apply(name="Stud")
            raise RuntimeError("boom")

    for beam in beams:
        assert beam.attrs.name == "Original"
    assert work.report.status is WorkStatus.ROLLED_BACK
    assert fake_cadwork.state.modified_undo_calls == []
    assert fake_cadwork.state.recreate_calls == []
    assert all(step.status is WorkStatus.ROLLED_BACK for step in work.report.steps)


def test_mid_apply_unknown_kwarg_still_restores_earlier_keys(fake_cadwork):
    beam = _make_beam()
    beam.attrs.name = "Original"

    with pytest.raises(TypeError, match="weight"):
        with WorkUnit([beam]) as work:
            work.apply(name="Stud", weight=12.0)

    assert beam.attrs.name == "Original"
    assert work.report.status is WorkStatus.ROLLED_BACK
    assert fake_cadwork.state.modified_undo_calls == []


def inner_job() -> int:
    return 42


def test_run_return_value_and_default_step_name(fake_cadwork):
    beam = _make_beam()
    with WorkUnit([beam]) as work:
        result = work.run(inner_job)
        named = work.run(inner_job, name="custom")

    assert result == 42
    assert named == 42
    assert work.report.steps[0].name == inner_job.__qualname__
    assert work.report.steps[1].name == "custom"


def test_two_runs_roll_back_together(fake_cadwork):
    beams = [_make_beam(), _make_beam()]
    for beam in beams:
        beam.attrs.name = "Original"

    def rename() -> None:
        work.apply(name="First")

    def boom() -> None:
        work.apply(group="frame")
        raise RuntimeError("second failed")

    with pytest.raises(RuntimeError, match="second failed"):
        with WorkUnit(beams) as work:
            work.run(rename)
            work.run(boom)

    for beam in beams:
        assert beam.attrs.name == "Original"
        assert beam.attrs.group == ""
    assert work.report.status is WorkStatus.ROLLED_BACK
    assert fake_cadwork.state.modified_undo_calls == []


def test_undo_records_one_call_with_tracked_ids(fake_cadwork):
    beams = [_make_beam(), _make_beam()]
    with WorkUnit(beams) as work:
        work.apply(name="Stud")

    assert fake_cadwork.state.modified_undo_calls == [[beams[0].id, beams[1].id]]
    assert work.report.status is WorkStatus.COMMITTED


def test_undo_false_records_none(fake_cadwork):
    beam = _make_beam()
    with WorkUnit([beam], undo=False) as work:
        work.apply(name="Stud")

    assert beam.attrs.name == "Stud"
    assert fake_cadwork.state.modified_undo_calls == []
    assert work.report.status is WorkStatus.COMMITTED


def test_rollback_records_no_undo(fake_cadwork):
    beam = _make_beam()
    with pytest.raises(ValueError):
        with WorkUnit([beam]) as work:
            work.apply(name="Stud")
            raise ValueError("nope")

    assert fake_cadwork.state.modified_undo_calls == []


def test_report_committed_diffs_vs_enter_snapshot(fake_cadwork):
    beam = _make_beam()
    beam.attrs.name = "Before"
    with WorkUnit([beam]) as work:
        work.apply(name="After")
        work.apply(group="frame")

    report = work.report
    assert report.status is WorkStatus.COMMITTED
    assert report.element_ids == (beam.id,)
    assert report.steps[0].name == "apply:name"
    assert report.steps[0].diffs[0].element_id == beam.id
    assert report.steps[0].diffs[0].attribute == "name"
    assert report.steps[0].diffs[0].before == "Before"
    assert report.steps[0].diffs[0].after == "After"
    # Second step diffs are versus enter, so they still include `name`.
    attributes = {diff.attribute: diff for diff in report.steps[1].diffs}
    assert attributes["name"].before == "Before"
    assert attributes["name"].after == "After"
    assert attributes["group"].before == ""
    assert attributes["group"].after == "frame"
    flattened = {(d.attribute, d.before, d.after) for d in report.diffs}
    assert ("name", "Before", "After") in flattened
    assert ("group", "", "frame") in flattened


def test_report_raises_until_exit(fake_cadwork):
    beam = _make_beam()
    with WorkUnit([beam]) as work:
        with pytest.raises(RuntimeError, match="report"):
            _ = work.report
        work.apply(name="Stud")
    assert work.report.status is WorkStatus.COMMITTED


def test_track_snapshots_current_attrs_not_pre_unit(fake_cadwork):
    original = _make_beam()
    original.attrs.name = "Original"
    late = _make_beam()
    late.attrs.name = "LateStart"

    with pytest.raises(RuntimeError, match="boom"):
        with WorkUnit([original]) as work:
            work.apply(name="Changed")
            late.attrs.name = "Discovered"
            work.track(late)
            work.apply(name="Both")
            raise RuntimeError("boom")

    assert original.attrs.name == "Original"
    assert late.attrs.name == "Discovered"
    assert work.report.status is WorkStatus.ROLLED_BACK


def test_apply_run_track_report_outside_context_raise(fake_cadwork):
    beam = _make_beam()
    work = WorkUnit([beam])
    with pytest.raises(RuntimeError, match="apply"):
        work.apply(name="X")
    with pytest.raises(RuntimeError, match="run"):
        work.run(lambda: None)
    with pytest.raises(RuntimeError, match="track"):
        work.track(beam)
    with pytest.raises(RuntimeError, match="report"):
        _ = work.report

    with WorkUnit([beam]) as inner:
        inner.apply(name="Stud")
    with pytest.raises(RuntimeError, match="apply"):
        inner.apply(name="Again")
    with pytest.raises(RuntimeError, match="run"):
        inner.run(lambda: None)
    with pytest.raises(RuntimeError, match="track"):
        inner.track(beam)
    assert inner.report.status is WorkStatus.COMMITTED


def test_empty_tracked_set_apply_is_noop(fake_cadwork):
    with WorkUnit() as work:
        work.apply(name="Stud")
    assert work.report.status is WorkStatus.COMMITTED
    assert work.report.element_ids == ()

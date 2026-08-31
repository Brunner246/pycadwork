"""Bulk live-model mutations with ``WorkUnit``.

``WorkUnit`` is a context manager over tracked live elements. It snapshots
``batch_apply`` attributes on enter, writes them with ``apply`` / ``run``,
restores them if a step raises, optionally registers one cadwork Undo step,
and freezes a ``WorkReport``. It is **not** ``persistence.UnitOfWork`` (that
one commits SQL).

    uv run python -m examples.work
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Point3D,
    RectSection,
    WorkUnit,
)


def _beams(*xs: float) -> list[Beam]:
    return [
        Beam.create_rectangular(
            RectSection(80, 200),
            AxisPoints(Point3D(x, 0, 0), Point3D(x + 2000, 0, 0), Point3D(x, 0, 1)),
        )
        for x in xs
    ]


def demo_apply(beams: list[Beam]) -> None:
    """Set the same attributes on many elements; a later typo would restore them all."""
    with WorkUnit(beams) as work:
        work.apply(name="Stud", group="frame")
    print("apply status =", work.report.status.value)
    print("names        =", {beam.attrs.name for beam in beams})
    print("groups       =", {beam.attrs.group for beam in beams})


def demo_run(beams: list[Beam]) -> None:
    """Run a callable inside the same unit. ``fn`` closes over the tracked set."""

    def relabel_openings() -> str:
        for beam in beams:
            beam.attrs.subgroup = "openings"
        return "labelled"

    with WorkUnit(beams) as work:
        result = work.run(relabel_openings, name="openings")
    print("run returned =", result)
    print("step name    =", work.report.steps[0].name)
    print("subgroups    =", {beam.attrs.subgroup for beam in beams})


def _fail() -> None:
    raise RuntimeError("mid-unit failure")


def demo_rollback(beams: list[Beam]) -> None:
    """An exception restores snapshotted attributes and freezes a rolled-back report."""
    for beam in beams:
        beam.attrs.name = "Original"
    try:
        with WorkUnit(beams) as work:
            work.apply(name="Stud")
            work.run(_fail, name="boom")
    except RuntimeError as exc:
        print("raised        =", exc)
    print("names        =", {beam.attrs.name for beam in beams})
    print("report.status =", work.report.status.value)


def demo_undo_false(beams: list[Beam]) -> None:
    """``undo=False`` still commits the attributes, but skips cadwork's Undo stack."""
    with WorkUnit(beams, undo=False) as work:
        work.apply(name="preview")
    print("undo=False status =", work.report.status.value)
    print("names             =", {beam.attrs.name for beam in beams})


def demo_report(beams: list[Beam]) -> None:
    """After exit, ``work.report.diffs`` is the before/after journal vs the snapshot."""
    for beam in beams:
        beam.attrs.name = "Stock"
        beam.attrs.group = ""
    with WorkUnit(beams) as work:
        work.apply(name="Stud", group="frame")
    print("report.status =", work.report.status.value)
    print("element_ids   =", work.report.element_ids)
    for diff in work.report.diffs:
        print(
            f"  id={diff.element_id} {diff.attribute}: {diff.before!r} -> {diff.after!r}"
        )


def run() -> None:
    """Run every work-unit demo in order."""
    demo_apply(_beams(0, 600))
    demo_run(_beams(1200, 1800))
    demo_rollback(_beams(2400, 3000))
    demo_undo_false(_beams(3600))
    demo_report(_beams(4200, 4800))


if __name__ == "__main__":
    run()

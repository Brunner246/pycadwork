"""Cross-cutting helpers: display-refresh suppression and bulk attribute writes.

cadwork repaints after every element mutation; for bulk work that costs more
than the work itself. ``DisplayRefreshScope`` drives the seam's
disable / recreate / enable triple, exception-safe. ``batch_apply`` writes one
attribute across many elements with a single adapter call each.

    uv run python -m examples.utilities
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    DisplayRefreshScope,
    Point3D,
    RectSection,
    auto_recreate,
    batch_apply,
)


def _beam(x: float) -> Beam:
    return Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(x, 0, 0), Point3D(x + 2000, 0, 0), Point3D(x, 0, 1)),
    )


def demo_display_scope_context() -> list[Beam]:
    """Suppress refresh during a bulk build; tracked elements recreate once, on exit."""
    with DisplayRefreshScope() as scope:
        beams = [_beam(x) for x in (0, 600, 1200)]
        scope.track(beams)  # scheduled for a single recreate when the block exits
    print("built", len(beams), "beams with one display recreate")
    return beams


@auto_recreate
def _build_frame() -> list[Beam]:
    """Create-and-track in one call: the returned elements are recreated on exit."""
    return [_beam(x) for x in (2000, 2600)]


def demo_auto_recreate_decorator() -> None:
    """`@auto_recreate` wraps a builder so its returned elements auto-recreate."""
    frame = _build_frame()
    print("decorator built", len(frame), "beams")


def demo_batch_apply(beams: list[Beam]) -> None:
    """Set the same attributes on many elements — one adapter call per attribute."""
    batch_apply(beams, group="frame", material_name="Pine")
    print("groups   =", {b.attrs.group for b in beams})
    print("materials =", {b.attrs.material_name for b in beams})

    # Unknown attribute names raise TypeError so typos surface at the call site.
    try:
        batch_apply(beams, colour="red")  # not a real attribute
    except TypeError as exc:
        print("rejected typo:", exc)


def run() -> None:
    """Run every utility demo in order."""
    beams = demo_display_scope_context()
    demo_auto_recreate_decorator()
    demo_batch_apply(beams)


if __name__ == "__main__":
    run()

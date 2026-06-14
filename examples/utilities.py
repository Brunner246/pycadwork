"""Cross-cutting helpers: display-refresh suppression and bulk attribute writes.

cadwork repaints after every element mutation; for bulk work that costs more
than the work itself. ``DisplayRefreshScope`` drives the seam's
disable / recreate / enable triple, exception-safe, and is usable as both a
context manager and a decorator. ``suppressed_display`` is its lighter sibling —
disable / enable with no recreate, for attribute-only work. ``batch_apply``
writes one attribute across many elements with a single adapter call each.

(These all drive the live cadwork display seam — for the pure-Python class
decorators ``auto_repr`` / ``auto_eq`` / ``deprecated`` see
:mod:`examples.decorators`.)

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
    suppressed_display,
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


def demo_recreate_after() -> list[Beam]:
    """`scope.recreate_after(fn)` calls a builder and tracks the Element(s) it returns.

    Same single-recreate-on-exit behaviour as ``track``, but the scope pulls the
    elements out of the builder's return value for you — no explicit ``track``.
    """
    with DisplayRefreshScope() as scope:
        beams = scope.recreate_after(lambda: [_beam(x) for x in (1800, 2400)])
    print("recreate_after built", len(beams), "beams")
    return beams


@DisplayRefreshScope()
def _build_decorated_frame() -> list[Beam]:
    """The scope as a decorator (note the parens — an instance is required).

    Returning Element(s) is *not* enough on its own: the decorator form does not
    auto-track. Reach for ``@auto_recreate`` when you want the return value
    tracked automatically; use ``@DisplayRefreshScope()`` when the function does
    its own ``scope.track`` or only needs refresh suspended.
    """
    return [_beam(x) for x in (3000, 3600)]


def demo_scope_as_decorator() -> None:
    """`@DisplayRefreshScope()` suspends refresh for the whole call."""
    frame = _build_decorated_frame()
    print("scope-decorated build made", len(frame), "beams")


@auto_recreate
def _build_frame() -> list[Beam]:
    """Create-and-track in one call: the returned elements are recreated on exit."""
    return [_beam(x) for x in (2000, 2600)]


def demo_auto_recreate_decorator() -> None:
    """`@auto_recreate` wraps a builder so its returned elements auto-recreate."""
    frame = _build_frame()
    print("decorator built", len(frame), "beams")


@suppressed_display
def _relabel(beams: list[Beam]) -> None:
    """Attribute-only mutation: no geometry changes, so no recreate is needed."""
    for beam in beams:
        beam.attrs.name = "Stud"
        beam.attrs.group = "frame"


def demo_suppressed_display(beams: list[Beam]) -> None:
    """`@suppressed_display` disables refresh during attribute-only work.

    Lighter than ``DisplayRefreshScope``: there is no recreate step, because the
    mutations don't change geometry — only names, groups, materials and the like.
    """
    _relabel(beams)
    print("relabelled", len(beams), "beams with refresh suppressed (no recreate)")


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
    demo_recreate_after()
    demo_scope_as_decorator()
    demo_auto_recreate_decorator()
    demo_suppressed_display(beams)
    demo_batch_apply(beams)


if __name__ == "__main__":
    run()

"""ElementRegistry — priority-ordered predicate dispatch (no live backend)."""
from __future__ import annotations

from pycadwork.cadwork_adapter.types import ElementTypeSnapshot
from pycadwork.element.registry import (
    AGGREGATE,
    GEOMETRIC,
    PRIMITIVE,
    SPECIAL,
    ElementRegistry,
    ensure_registered,
)


class _Beam:
    pass


class _Wall:
    pass


class _Line:
    pass


def test_resolve_returns_only_match():
    reg = ElementRegistry()
    reg.register(lambda s: s.is_beam, _Beam, PRIMITIVE)
    assert reg.resolve(ElementTypeSnapshot(is_beam=True)) is _Beam
    assert reg.resolve(ElementTypeSnapshot(is_panel=True)) is None


def test_aggregate_priority_beats_primitive_when_both_match():
    reg = ElementRegistry()
    # Registration order deliberately wrong (primitive first) to prove the band,
    # not insertion order, decides: a cover also satisfies the beam predicate.
    reg.register(lambda s: s.is_beam, _Beam, PRIMITIVE)
    reg.register(lambda s: s.is_wall, _Wall, AGGREGATE)

    snap = ElementTypeSnapshot(is_beam=True, is_wall=True)
    assert reg.resolve(snap) is _Wall


def test_tie_break_is_insertion_order_within_a_band():
    reg = ElementRegistry()
    first_match = type("First", (), {})
    second_match = type("Second", (), {})
    reg.register(lambda s: s.is_line, first_match, GEOMETRIC)
    reg.register(lambda s: s.is_line, second_match, GEOMETRIC)

    assert reg.resolve(ElementTypeSnapshot(is_line=True)) is first_match


def test_no_match_returns_none():
    reg = ElementRegistry()
    reg.register(lambda s: s.is_surface, _Line, GEOMETRIC)
    assert reg.resolve(ElementTypeSnapshot(is_beam=True)) is None


def test_resolve_resorts_after_late_registration():
    reg = ElementRegistry()
    reg.register(lambda s: s.is_beam, _Beam, PRIMITIVE)
    assert reg.resolve(ElementTypeSnapshot(is_beam=True, is_wall=True)) is _Beam

    # Add a higher-priority entry after a resolve already sorted the table.
    reg.register(lambda s: s.is_wall, _Wall, AGGREGATE)
    assert reg.resolve(ElementTypeSnapshot(is_beam=True, is_wall=True)) is _Wall


def test_ensure_registered_is_idempotent():
    from pycadwork.element.registry import REGISTRY

    ensure_registered()
    count = len(REGISTRY._entries)
    ensure_registered()
    assert len(REGISTRY._entries) == count


def test_priority_bands_are_strictly_ordered():
    assert AGGREGATE < SPECIAL < PRIMITIVE < GEOMETRIC

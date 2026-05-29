"""Declarative dispatch registry for :func:`pycadwork.element.from_id`.

Each concrete wrapper class registers itself with a predicate over an
:class:`ElementTypeSnapshot` and a *priority band*. ``from_id`` consults the
registry sorted by priority, so dispatch order is explicit numbers rather than
the position of a row in a hand-maintained list.

Why bands and not a single ``sorted`` list: a cover element also satisfies the
primitive ``is_beam`` / ``is_panel`` predicates, so aggregates (``Wall`` / ``Slab``
/ ``Roof``) must be checked *before* primitives. The bands below encode that — a
lower number is checked first; gaps of ten leave room to slot future kinds in
without renumbering.

Registration happens at class-definition time via :func:`register_element`. Since
the cover modules import :class:`Element` from this package, their import is
deferred to :func:`ensure_registered` (called once by ``from_id``) — the same
circular-import dodge the old static table used.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, TypeVar

from pycadwork.cadwork_adapter.types import ElementTypeSnapshot

_T = TypeVar("_T", bound=type)

Predicate = Callable[[ElementTypeSnapshot], bool]

# Priority bands — lower is checked first.
AGGREGATE = 10  # Wall / Slab / Roof — must beat the primitive predicates
SPECIAL = 20  # Drilling / ConnectorAxis / Opening / Auxiliary
PRIMITIVE = 30  # Beam / Plate
GEOMETRIC = 40  # Node / Surface / Line


@dataclass(frozen=True, slots=True, order=True)
class _Entry:
    """A sortable dispatch row. Only ``sort_index`` participates in ordering."""

    sort_index: tuple[int, int]  # (priority, insertion sequence)
    predicate: Predicate = field(compare=False)
    cls: type = field(compare=False)


class ElementRegistry:
    """A priority-ordered table mapping type predicates to ``Element`` subclasses."""

    __slots__ = ("_entries", "_seq", "_sorted")

    def __init__(self) -> None:
        self._entries: list[_Entry] = []
        self._seq = 0
        self._sorted = True

    def register(self, predicate: Predicate, cls: type, priority: int) -> None:
        """Record ``cls`` under ``predicate`` at ``priority`` (lower = checked first).

        Ties within a band break by registration order, so a more specific class
        registered first still wins over a later, broader one at the same priority.
        """
        self._entries.append(_Entry((priority, self._seq), predicate, cls))
        self._seq += 1
        self._sorted = False

    def resolve(self, snapshot: ElementTypeSnapshot) -> type | None:
        """Return the highest-priority class whose predicate matches, or ``None``."""
        if not self._sorted:
            self._entries.sort()
            self._sorted = True
        for entry in self._entries:
            if entry.predicate(snapshot):
                return entry.cls
        return None


# The package-wide registry consulted by ``from_id``.
REGISTRY = ElementRegistry()


def register_element(
    predicate: Predicate, *, priority: int
) -> Callable[[_T], _T]:
    """Class decorator: register the decorated ``Element`` subclass for dispatch.

    ``predicate`` receives an :class:`ElementTypeSnapshot`; ``priority`` is one of
    the bands in this module (``AGGREGATE`` < ``SPECIAL`` < ``PRIMITIVE`` <
    ``GEOMETRIC``). Custom subclasses can register themselves the same way::

        @register_element(lambda s: s.is_beam, priority=PRIMITIVE)
        class MyBeam(Beam): ...
    """

    def decorate(cls: _T) -> _T:
        REGISTRY.register(predicate, cls, priority)
        return cls

    return decorate


_loaded = False


def ensure_registered() -> None:
    """Import every wrapper module once so its ``@register_element`` runs.

    Idempotent. The cover imports are deferred to here (not module top) to break
    the ``cover.* -> element.base`` import cycle — exactly where the dispatch table
    used to be built.
    """
    global _loaded
    if _loaded:
        return
    _loaded = True

    # Primitive / special elements (most are already imported via element/__init__,
    # but list them explicitly so registration never depends on import order).
    import pycadwork.element.auxiliary  # noqa: F401
    import pycadwork.element.beam  # noqa: F401
    import pycadwork.element.connector_axis  # noqa: F401
    import pycadwork.element.drilling  # noqa: F401
    import pycadwork.element.node  # noqa: F401
    import pycadwork.element.opening  # noqa: F401
    import pycadwork.element.plate  # noqa: F401
    import pycadwork.element.surface  # noqa: F401

    # Aggregates — deferred to avoid the circular import.
    import pycadwork.cover.roof  # noqa: F401
    import pycadwork.cover.slab  # noqa: F401
    import pycadwork.cover.wall  # noqa: F401

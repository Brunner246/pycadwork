"""``from_id`` — wrap an existing cadwork element in the right subclass.

Dispatch reads ``ElementTypeSnapshot`` once (via the backend) and consults the
declarative :data:`REGISTRY`. Each wrapper class registers its own predicate and
priority via ``@register_element`` at its definition site; see
:mod:`pycadwork.element.registry` for the priority bands and why aggregates are
checked before primitives.
"""

from __future__ import annotations

import warnings
from typing import Any

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.registry import REGISTRY, ensure_registered


def from_id(eid: int) -> Element[Any]:
    """Wrap an existing cadwork element ID in the most specific subclass.

    Falls back to a bare :class:`Element` (with a warning) if no predicate
    matches — that means cadwork has a type we haven't taught the OOP layer
    about yet.
    """
    ensure_registered()

    snap = cadwork.elements.get_element_type(int(eid))
    cls = REGISTRY.resolve(snap)
    if cls is None:
        warnings.warn(
            f"from_id({eid!r}): no specific subclass matched; returning bare Element",
            stacklevel=2,
        )
        cls = Element

    instance = cls(int(eid))
    # share the cached snapshot — we just paid for it
    instance._type = snap
    return instance

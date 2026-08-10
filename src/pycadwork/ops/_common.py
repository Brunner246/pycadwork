"""Module-private input normalization shared by the ops functions.

Every multi-element ops parameter accepts a single :class:`Element` or any
iterable of them; ``_as_elements`` collapses both shapes to a list.
"""

from __future__ import annotations

from collections.abc import Iterable

from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element.base import Element


def _as_elements(value: Element | Iterable[Element]) -> list[Element]:
    if isinstance(value, Element):
        return [value]
    return list(value)


def _ids(elements: Iterable[Element]) -> list[ElementId]:
    return [e.id for e in elements]

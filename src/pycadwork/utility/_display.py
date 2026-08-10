"""Display-refresh orchestration helpers.

cadwork repaints its view after every element mutation; for bulk work that
costs more than the work itself. The helpers here drive the seam's
disable / recreate / enable triple in an exception-safe way and never
import cadwork directly.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from contextlib import ContextDecorator
from functools import wraps
from typing import TypeVar

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element import Element

R = TypeVar("R")


class DisplayRefreshScope(ContextDecorator):
    """Suspend cadwork's auto display refresh for the duration of a block.

    Tracked elements are passed to ``recreate_elements`` on exit, before
    refresh is re-enabled. Safe under exceptions: refresh is always
    re-enabled. On a raised exception the recreate step is skipped so the
    view state matches the (rolled-back) runtime state.

    Usage as a context manager::

        with DisplayRefreshScope() as scope:
            beams = [Beam.create_rectangular(...) for ...]
            scope.track(beams)

    Usage as a decorator (note the parens — an instance is required)::

        @DisplayRefreshScope()
        def build_frame() -> list[Beam]: ...
    """

    def __init__(self) -> None:
        self._to_recreate: list[ElementId] = []

    def __enter__(self) -> "DisplayRefreshScope":
        cadwork.display.disable_auto_display_refresh()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            if exc_type is None and self._to_recreate:
                cadwork.display.recreate_elements(self._to_recreate)
        finally:
            cadwork.display.enable_auto_display_refresh()
        return False

    def track(
        self, elements: Element | Iterable[Element]
    ) -> Element | Iterable[Element]:
        """Schedule one or more elements for recreate on scope exit.

        Returns the input unchanged so callers can chain.
        """
        if isinstance(elements, Element):
            self._to_recreate.append(elements.id)
        else:
            self._to_recreate.extend(e.id for e in elements)
        return elements

    def recreate_after(self, func: Callable[..., R], /, *args, **kwargs) -> R:
        """Call ``func``, track any :class:`Element`(s) it returns, return result."""
        result = func(*args, **kwargs)
        if isinstance(result, Element):
            self.track(result)
        elif isinstance(result, Iterable):
            elements = [r for r in result if isinstance(r, Element)]
            if elements:
                self.track(elements)
        return result


def suppressed_display(func: Callable[..., R]) -> Callable[..., R]:
    """Disable auto display refresh for the duration of ``func``.

    Like :class:`DisplayRefreshScope` but without the recreate step — use
    when ``func`` mutates only attributes that don't change geometry.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> R:
        display = cadwork.display
        display.disable_auto_display_refresh()
        try:
            return func(*args, **kwargs)
        finally:
            display.enable_auto_display_refresh()

    return wrapper


def auto_recreate(func: Callable[..., R]) -> Callable[..., R]:
    """Run ``func`` inside a :class:`DisplayRefreshScope`, auto-tracking its return.

    If ``func`` returns an :class:`Element` (or iterable of them) those are
    recreated on exit. Sugar over ``DisplayRefreshScope().recreate_after(func)``
    for the common single-call create-and-track pattern.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> R:
        with DisplayRefreshScope() as scope:
            return scope.recreate_after(func, *args, **kwargs)

    return wrapper

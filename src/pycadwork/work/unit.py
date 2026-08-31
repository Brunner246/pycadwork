"""WorkUnit — a compensating context manager over live-element attributes.

Not :class:`pycadwork.persistence.UnitOfWork` (that commits SQL records).
This type snapshots ``batch_apply`` attributes, restores them on exception,
optionally registers a cadwork Undo step on success, and freezes a
:class:`~pycadwork.work.report.WorkReport`.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable
from dataclasses import replace

from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import ElementId
from pycadwork.element import Element
from pycadwork.utility import DisplayRefreshScope, batch_apply
from pycadwork.utility._batch import _BATCH_SETTERS
from pycadwork.work.report import AttributeDiff, WorkReport, WorkStatus, WorkStep


def _as_elements(value: Element | Iterable[Element]) -> tuple[Element, ...]:
    if isinstance(value, Element):
        return (value,)
    return tuple(value)


def _read_batch_attrs(element: Element) -> dict[str, object]:
    attrs = element.attrs
    return {key: getattr(attrs, key) for key in _BATCH_SETTERS}


class WorkUnit:
    """Context manager over a tracked set of live :class:`~pycadwork.element.Element`s.

    Inside the block call :meth:`apply` (bulk attribute writes) and
    :meth:`run` (arbitrary callables). On enter, every tracked element's
    ``batch_apply`` attributes are snapshotted. On exception those snapshots
    are restored, viewport recreate is skipped, cadwork Undo is not touched,
    and a rolled-back report is frozen before the exception re-raises. On
    success tracked elements are recreated once and registered with
    ``add_modified_elements_to_undo`` unless ``undo=False``.
    """

    def __init__(
        self,
        elements: Iterable[Element] = (),
        *,
        undo: bool = True,
    ) -> None:
        self._undo = undo
        self._initial: tuple[Element, ...] = tuple(elements)
        self._elements: list[Element] = []
        self._seen_ids: set[ElementId] = set()
        self._snapshots: dict[ElementId, dict[str, object]] = {}
        self._steps: list[WorkStep] = []
        self._report: WorkReport | None = None
        self._active = False
        self._scope: DisplayRefreshScope | None = None

    @property
    def elements(self) -> tuple[Element, ...]:
        if self._elements:
            return tuple(self._elements)
        return self._initial

    @property
    def report(self) -> WorkReport:
        if self._report is None:
            raise RuntimeError("WorkUnit.report is only available after the unit exits")
        return self._report

    def __enter__(self) -> WorkUnit:
        self._scope = DisplayRefreshScope()
        self._scope.__enter__()
        self._active = True
        try:
            for element in self._initial:
                self.track(element)
        except Exception:
            self._active = False
            self._scope.__exit__(*sys.exc_info())
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        restore_error: BaseException | None = None
        try:
            if exc_type is not None:
                try:
                    self._restore()
                except Exception as err:
                    restore_error = err
                self._freeze(WorkStatus.ROLLED_BACK)
            else:
                if self._undo:
                    cadwork.elements.add_modified_elements_to_undo(
                        [element.id for element in self._elements]
                    )
                self._freeze(WorkStatus.COMMITTED)
        finally:
            self._active = False
            assert self._scope is not None
            suppressed = self._scope.__exit__(exc_type, exc, tb)
        if restore_error is not None:
            raise restore_error from exc
        return suppressed

    def track(self, elements: Element | Iterable[Element]) -> None:
        """Add elements to the tracked set and snapshot their current attrs."""
        self._require_active("track")
        assert self._scope is not None
        for element in _as_elements(elements):
            if element.id in self._seen_ids:
                continue
            self._seen_ids.add(element.id)
            self._elements.append(element)
            self._snapshots[element.id] = _read_batch_attrs(element)
            self._scope.track(element)

    def apply(self, **attrs: object) -> None:
        """Write ``attrs`` onto every tracked element via :func:`batch_apply`."""
        self._require_active("apply")
        step_name = f"apply:{','.join(attrs)}" if attrs else "apply"
        try:
            batch_apply(self.elements, **attrs)
        except Exception:
            self._record_step(step_name, WorkStatus.ROLLED_BACK)
            raise
        self._record_step(step_name, WorkStatus.COMMITTED)

    def run(self, fn: Callable[[], object], *, name: str | None = None) -> object:
        """Call ``fn()`` and record it as a step. Return value is passed through."""
        self._require_active("run")
        step_name = fn.__qualname__ if name is None else name
        try:
            result = fn()
        except Exception:
            self._record_step(step_name, WorkStatus.ROLLED_BACK)
            raise
        self._record_step(step_name, WorkStatus.COMMITTED)
        return result

    def _require_active(self, verb: str) -> None:
        if not self._active:
            raise RuntimeError(
                f"WorkUnit.{verb} requires an active context (use `with WorkUnit(...)`)"
            )

    def _record_step(self, name: str, status: WorkStatus) -> None:
        self._steps.append(WorkStep(name=name, status=status, diffs=self._diffs_from_snapshot()))

    def _diffs_from_snapshot(self) -> tuple[AttributeDiff, ...]:
        diffs: list[AttributeDiff] = []
        for element in self._elements:
            before = self._snapshots[element.id]
            current = _read_batch_attrs(element)
            for key in _BATCH_SETTERS:
                if current[key] != before[key]:
                    diffs.append(
                        AttributeDiff(
                            element_id=int(element.id),
                            attribute=key,
                            before=before[key],
                            after=current[key],
                        )
                    )
        return tuple(diffs)

    def _restore(self) -> None:
        groups: dict[tuple[str, object], list[Element]] = {}
        for element in self._elements:
            before = self._snapshots[element.id]
            current = _read_batch_attrs(element)
            for key, value in before.items():
                if current[key] != value:
                    groups.setdefault((key, value), []).append(element)
        for (key, value), group in groups.items():
            batch_apply(group, **{key: value})

    def _freeze(self, status: WorkStatus) -> None:
        if status is WorkStatus.ROLLED_BACK:
            steps = tuple(replace(step, status=WorkStatus.ROLLED_BACK) for step in self._steps)
        else:
            steps = tuple(self._steps)
        self._report = WorkReport(
            status=status,
            element_ids=tuple(int(element.id) for element in self._elements),
            steps=steps,
        )

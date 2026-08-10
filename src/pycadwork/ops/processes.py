"""Process management: extract cutting bodies (Ctrl+D) and restore.

:func:`extract_cutting_bodies` materializes the cutting bodies of every
process on the given elements and deletes the processes — cadwork's Ctrl+D
action — grouped per source element. :func:`cutting_bodies` wraps that in a
context manager that restores the model on exit by re-subtracting the
surviving bodies from their sources and deleting them.

The restore reproduces the cut *geometry* via boolean subtraction; it does
not reinstate the parametric processes or end types themselves.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from pycadwork.cadwork_adapter import cadwork
from pycadwork.element.base import Element
from pycadwork.element.factory import from_id
from pycadwork.ops._common import _as_elements, _ids


@dataclass(frozen=True, slots=True)
class CuttingBodyExtraction:
    """Cutting bodies grouped per source element.

    Keys of :attr:`by_source` are the caller's own :class:`Element`
    instances (hashable by ``(type, id)``), in extraction order. A source
    without processes maps to an empty list.
    """

    by_source: dict[Element, list[Element]]

    @property
    def sources(self) -> list[Element]:
        """The source elements, in extraction order."""
        return list(self.by_source)

    @property
    def bodies(self) -> list[Element]:
        """All cutting bodies, flattened in source order."""
        return [body for bodies in self.by_source.values() for body in bodies]


def extract_cutting_bodies(
    elements: Element | Iterable[Element],
    *,
    cutting_elements_only: bool = True,
) -> CuttingBodyExtraction:
    """Extract process cutting bodies (Ctrl+D), grouped per source element.

    The processes are deleted from the sources; the bodies stay in the model
    as auxiliary elements. cwapi3d returns one flat list per call, so the
    per-source grouping costs one adapter call per element — a deliberate
    trade-off for a tooling workflow, not a hot loop.
    """
    by_source: dict[Element, list[Element]] = {}
    for source in _as_elements(elements):
        body_ids = cadwork.operations.delete_processes_keep_cutting_bodies(
            [source.id], cutting_elements_only
        )
        by_source[source] = [from_id(eid) for eid in body_ids]
    return CuttingBodyExtraction(by_source=by_source)


def delete_processes(elements: Element | Iterable[Element]) -> None:
    """Delete all processes of ``elements`` (cutting bodies are not kept)."""
    cadwork.operations.delete_all_element_processes(_ids(_as_elements(elements)))


def delete_end_types(elements: Element | Iterable[Element]) -> None:
    """Delete all end types of ``elements``."""
    cadwork.operations.delete_all_element_end_types(_ids(_as_elements(elements)))


def _restore(extraction: CuttingBodyExtraction) -> None:
    """Re-subtract surviving bodies from their sources, then delete them.

    Bodies (or sources) the user deleted inside the block are tolerated
    no-ops; the split-off return of the subtraction is ignored.
    """
    for source, bodies in extraction.by_source.items():
        surviving = [
            body.id for body in bodies if cadwork.elements.element_exists(body.id)
        ]
        if not surviving:
            continue
        if cadwork.elements.element_exists(source.id):
            cadwork.operations.subtract_elements(surviving, [source.id])
        cadwork.elements.delete_elements(surviving)


@contextmanager
def cutting_bodies(
    elements: Element | Iterable[Element],
    *,
    cutting_elements_only: bool = True,
) -> Iterator[CuttingBodyExtraction]:
    """Extract process cutting bodies, restoring the cut geometry on exit.

    The restore runs in a ``finally`` block — also when the body raises —
    so the model never stays in the processes-stripped state. Exceptions
    from the block propagate after the restore.
    """
    extraction = extract_cutting_bodies(
        elements, cutting_elements_only=cutting_elements_only
    )
    try:
        yield extraction
    finally:
        _restore(extraction)

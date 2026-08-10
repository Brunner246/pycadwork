"""``Document`` — the top-level handle for the active cadwork project.

A ``Document`` does two jobs:

* **Manages the project** — its :attr:`project` component (a
  :class:`~pycadwork.document.project.ProjectInfo`) exposes the project GUID
  and the rest of the project metadata, mirroring how an
  :class:`~pycadwork.element.base.Element` exposes ``element.attrs``.
* **Is the element repository** — a *live* view over the whole model.
  :meth:`elements`, :meth:`active`, :meth:`elements_of`, :meth:`get`,
  :meth:`delete` and :meth:`covers` all query the backend at call time and wrap
  ids via :func:`~pycadwork.element.factory.from_id`. There is no cached state,
  in keeping with :class:`Element` / :class:`~pycadwork.element.cover.group.Group` /
  :func:`~pycadwork.element.cover.discover.discover_covers`, which are all live views.

There is exactly one active project, so ``Document()`` always refers to it;
construction takes no arguments.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar

from pycadwork.cadwork_adapter import cadwork
from pycadwork.document.guard import is_3d_document
from pycadwork.document.project import ProjectInfo
from pycadwork.element.base import Element
from pycadwork.element.cover.aggregate import Aggregate
from pycadwork.element.cover.discover import discover_covers
from pycadwork.element.factory import from_id
from pycadwork.utility import DisplayRefreshScope

if TYPE_CHECKING:
    # Type-only: pycadwork.versioning imports Document, so importing SyncPlan at
    # runtime here would cycle back. apply_sync() imports it lazily instead.
    from pycadwork.versioning._sync import SyncPlan

# ``Element[Any]`` not bare ``Element``: ``Element`` is generic and invariant in
# its geometry parameter, so ``bound=Element`` would reject specialized
# subclasses like ``Beam`` at call sites such as ``elements_of(Beam)``.
E = TypeVar("E", bound="Element[Any]")


class Document:
    """Project handle and live-query repository over the active model."""

    __slots__ = ("project",)

    def __init__(self) -> None:
        self.project: ProjectInfo = ProjectInfo()

    @property
    def guid(self) -> str:
        """The project GUID — convenience delegate to :attr:`project`."""
        return self.project.guid

    @property
    def file_name(self) -> str:
        """The active 3D document's file name (empty if unsaved / unavailable)."""
        return cadwork.project.get_3d_file_name()

    @property
    def file_path(self) -> str:
        """The active 3D document's full path (empty if unsaved / unavailable)."""
        return cadwork.project.get_3d_file_path()

    def is_3d(self) -> bool:
        """True iff the active document is a 3D model. See :func:`is_3d_document`."""
        return is_3d_document()

    def save(self) -> None:
        """Persist the active 3D document to disk in place (silently)."""
        cadwork.project.save_3d_file()

    def reload_from(self, path: str | Path) -> int:
        """Replace the live model with the elements in the ``.3dc`` at ``path``.

        Deletes every identifiable element, then imports ``path`` into the active
        document — a full-fidelity restore (real geometry, every element type),
        unlike the best-effort JSON write-back which never moves existing
        elements. ``import_3dc_file`` is *additive*, so the delete-all comes
        first; both run inside a :class:`DisplayRefreshScope` so the viewport
        refreshes once at the end. The imported elements get fresh cadwork ids
        (the file's stored ids are not preserved). Returns the number of
        identifiable elements present afterwards (the imported set, since the
        model was emptied first).
        """
        with DisplayRefreshScope():
            cadwork.elements.delete_elements([e.id for e in self.elements()])
            cadwork.file.import_3dc_file(str(path))
        return len(cadwork.elements.get_all_identifiable_element_ids())

    def apply_sync(self, plan: "SyncPlan", binary_path: str | Path) -> int:
        """Reconcile the live model to ``plan`` with minimal churn; return elements added.

        Deletes ``plan.stale`` first. If ``plan.missing`` is empty, stops right
        there — **no import at all** (the actual "smart" payoff: a pure-removal
        switch never touches the binary). Otherwise imports ``binary_path``
        (additive, so it brings in a fresh copy of *every* target element,
        unchanged ones included, each with a fresh id/GUID), fingerprints just
        the freshly-imported ids, and deletes whichever of them duplicate
        something ``plan.unchanged`` already covers — so only the true delta
        survives. Runs inside a :class:`DisplayRefreshScope` for a single
        recreate on exit.
        """
        from pycadwork.persistence.mappers import ModelReader
        from pycadwork.versioning._sync import fingerprint_snapshot

        survivors: list[int] = []
        with DisplayRefreshScope() as scope:
            if plan.stale:
                cadwork.elements.delete_elements(list(plan.stale))
            if not plan.missing:
                return 0

            ids_before = set(cadwork.elements.get_all_identifiable_element_ids())
            cadwork.file.import_3dc_file(str(binary_path))
            fresh_ids = [
                eid
                for eid in cadwork.elements.get_all_identifiable_element_ids()
                if eid not in ids_before
            ]

            fresh_fingerprints = fingerprint_snapshot(ModelReader().read())
            remaining = Counter(plan.missing)
            stale_duplicates: list[int] = []
            for eid in fresh_ids:
                fingerprint = fresh_fingerprints.get(eid)
                if fingerprint is not None and remaining.get(fingerprint, 0) > 0:
                    remaining[fingerprint] -= 1
                    survivors.append(eid)
                else:
                    stale_duplicates.append(eid)

            if stale_duplicates:
                cadwork.elements.delete_elements(stale_duplicates)
            if survivors:
                scope.track([from_id(eid) for eid in survivors])
        return len(survivors)

    # ---- repository ----

    @staticmethod
    def elements() -> list[Element[Any]]:
        """Every identifiable element in the model, wrapped by type."""
        eids = cadwork.elements.get_all_identifiable_element_ids()
        return [from_id(eid) for eid in eids]

    @staticmethod
    def active() -> list[Element[Any]]:
        """The currently active (selected) identifiable elements."""
        eids = cadwork.elements.get_active_identifiable_element_ids()
        return [from_id(eid) for eid in eids]

    def elements_of(self, cls: type[E]) -> list[E]:
        """Subset of :meth:`elements` whose runtime type is ``cls`` or a subclass.

        The parameterized helper subsumes any per-type accessor — adding a new
        element subclass never requires a new method here.
        """
        return [e for e in self.elements() if isinstance(e, cls)]

    @staticmethod
    def get(eid: int) -> Element[Any]:
        """Wrap a single existing element id in its most specific subclass."""
        return from_id(eid)

    @staticmethod
    def delete(elements: Iterable[Element[Any]]) -> None:
        """Delete the given elements from the model in one batched call."""
        cadwork.elements.delete_elements([e.id for e in elements])

    @staticmethod
    def covers() -> list[Aggregate]:
        """All cover aggregates (``Wall`` / ``Slab`` / ``Roof``) in the model."""
        eids = cadwork.elements.get_all_identifiable_element_ids()
        return discover_covers(eids)

    def __repr__(self) -> str:
        return f"Document(guid={self.project.guid!r}, name={self.project.name!r})"

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

from collections.abc import Iterable
from typing import Any, TypeVar

from pycadwork.cadwork_adapter import cadwork
from pycadwork.document.guard import is_3dc_document
from pycadwork.document.project import ProjectInfo
from pycadwork.element.base import Element
from pycadwork.element.cover.aggregate import Aggregate
from pycadwork.element.cover.discover import discover_covers
from pycadwork.element.factory import from_id

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
    def file_name_3dc(self) -> str:
        """The active 3d document's file name (empty if unsaved / unavailable)."""
        return cadwork.project.get_3d_file_name()

    def is_3dc(self) -> bool:
        """True iff the active document is a 3dc model. See :func:`is_3dc_document`."""
        return is_3dc_document()

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

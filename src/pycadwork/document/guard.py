"""Guard a block of work to a 3dc (3D) cadwork document.

Detail elements — and most model-mutating work — only make sense inside a 3D
(``.3dc``) document. cwapi3d does not refuse such calls in, say, a 2D plan, so
this module offers a fail-fast guard a caller wraps around the work::

    from pycadwork.document import require_3dc_document
    from pycadwork.detail import build_detail

    with require_3dc_document():
        build_detail(definition)

The predicate is intentionally simple — a 3dc document iff its file name is
non-empty and ends ``.3dc`` (case-insensitive). cwapi3d's function is literally
``get_3d_file_name``; the pycadwork-level names here use the ``3dc`` document
type the file extension denotes.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from pycadwork.cadwork_adapter import cadwork


class NotA3dcDocumentError(RuntimeError):
    """The active cadwork document is not a 3dc model."""


def current_3dc_file_name() -> str:
    """The active 3d document's file name (empty if unsaved / unavailable)."""
    return cadwork.project.get_3d_file_name()


def is_3dc_document() -> bool:
    """True iff the active document is a 3dc model (non-empty name ending ``.3dc``)."""
    name = current_3dc_file_name()
    return bool(name) and name.lower().endswith(".3dc")


@contextmanager
def require_3dc_document() -> Iterator[None]:
    """Guard a block to a 3dc document; raise :class:`NotA3dcDocumentError` otherwise.

    Usable as a context manager or a decorator — ``contextlib.contextmanager``
    results are ``ContextDecorator`` instances.
    """
    if not is_3dc_document():
        raise NotA3dcDocumentError(
            f"active document {current_3dc_file_name()!r} is not a 3dc model"
        )
    yield

"""Guard a block of work to a 3D cadwork document.

Most model-mutating work only makes sense inside a 3D document. cwapi3d does
not refuse such calls in, say, a 2D plan, so this module offers a fail-fast
guard a caller wraps around the work::

    from pycadwork.document import require_3d_document

    with require_3d_document():
        ...  # create / edit elements here

The predicate is intentionally simple — a 3D document iff its file name is
non-empty and carries a 3D extension (``.3d`` or ``.3dc``, case-insensitive).
A cadwork 3D model may be saved under either extension, so both count; the
``3dc``-only check this replaced wrongly rejected plain ``.3d`` models. cwapi3d's
function is literally ``get_3d_file_name``, and these pycadwork-level names follow
it.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from pycadwork.cadwork_adapter import cadwork

#: File extensions a cadwork 3D model may be saved under (lower-case).
THREE_D_EXTENSIONS: tuple[str, ...] = (".3d", ".3dc")


class NotA3dDocumentError(RuntimeError):
    """The active cadwork document is not a 3D model."""


def current_3d_file_name() -> str:
    """The active 3D document's file name (empty if unsaved / unavailable)."""
    return cadwork.project.get_3d_file_name()


def is_3d_document() -> bool:
    """True iff the active document is a 3D model (name ends ``.3d`` / ``.3dc``)."""
    return current_3d_file_name().lower().endswith(THREE_D_EXTENSIONS)


@contextmanager
def require_3d_document() -> Iterator[None]:
    """Guard a block to a 3D document; raise :class:`NotA3dDocumentError` otherwise.

    Usable as a context manager or a decorator — ``contextlib.contextmanager``
    results are ``ContextDecorator`` instances.
    """
    if not is_3d_document():
        raise NotA3dDocumentError(
            f"active document {current_3d_file_name()!r} is not a 3D model"
        )
    yield

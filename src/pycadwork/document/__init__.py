"""The ``Document``: project handle plus live-query element repository."""

from __future__ import annotations

from pycadwork.document.document import Document
from pycadwork.document.guard import (
    NotA3dDocumentError,
    current_3d_file_name,
    is_3d_document,
    require_3d_document,
)
from pycadwork.document.project import ProjectInfo

__all__ = [
    "Document",
    "NotA3dDocumentError",
    "ProjectInfo",
    "current_3d_file_name",
    "is_3d_document",
    "require_3d_document",
]

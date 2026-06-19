"""The ``Document``: project handle plus live-query element repository."""

from __future__ import annotations

from pycadwork.document.document import Document
from pycadwork.document.guard import (
    NotA3dcDocumentError,
    current_3dc_file_name,
    is_3dc_document,
    require_3dc_document,
)
from pycadwork.document.project import ProjectInfo

__all__ = [
    "Document",
    "NotA3dcDocumentError",
    "ProjectInfo",
    "current_3dc_file_name",
    "is_3dc_document",
    "require_3dc_document",
]

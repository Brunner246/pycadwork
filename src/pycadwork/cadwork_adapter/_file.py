"""FileAdapter: importing/exporting model files (``file_controller``).

cadwork's ``file_controller`` is the surface for reading and writing model files
on disk. The versioning bridge uses it to bring a *committed* ``.3dc`` back into
the running model: a full-fidelity restore that the JSON write-back
(``persistence.ModelWriter``) cannot match, because it reconstructs every element
type and the exact geometry the file holds.

``import_3dc_file`` imports the file's elements **into the active document** — it
adds, it does not replace — so a caller wanting a clean restore deletes the live
elements first (see :meth:`pycadwork.document.Document.reload_from`).

Adding a new call here means mirroring it on ``FakeFileAdapter`` in
``tests/_fakes/cadwork_adapter.py`` and wiring the ``file`` slot in
``tests/conftest.py``.
"""

from __future__ import annotations


class FileAdapter:
    """Read/write cadwork model files via ``file_controller``."""

    def import_3dc_file(self, path: str) -> None:
        """Import the ``.3dc`` at ``path`` into the active document (additive)."""
        import file_controller

        file_controller.import_3dc_file(path)

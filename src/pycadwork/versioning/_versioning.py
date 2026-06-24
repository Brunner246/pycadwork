"""ModelVersioning — the bridge from the live cadwork model to a git repository.

This is the only versioning code that touches cadwork, and it does so only
through the persistence pipeline (:class:`~pycadwork.persistence.ModelReader` /
:class:`~pycadwork.persistence.ModelWriter` / :func:`~pycadwork.persistence.diff`)
plus the one new save seam (:meth:`pycadwork.document.Document.save`). It owns no
git logic of its own — every git operation is delegated to an injected
:class:`~pycadwork.versioning.Repository`.

The bridge is **model ⇄ snapshot ⇄ diffable text ⇄ git**:

* :meth:`commit` losslessly captures the model — it saves the ``.3dc``, projects
  the model to a :class:`~pycadwork.persistence.records.ModelSnapshot`, writes the
  deterministic JSONL tree (the reviewable artifact) plus the binary ``.3dc`` (the
  full-fidelity artifact), and commits both.
* :meth:`restore` (alias :meth:`load`) brings a version *back*. Its **primary**
  guarantee is the working-tree ``.3dc`` path to reopen in cadwork — full
  fidelity. The optional ``apply_to_model=True`` additionally runs the
  *best-effort* JSON write-back through ``ModelWriter`` (see the module-level
  limitations in the package docstring: existing points are never moved,
  non-reconstructable types are skipped).

Direction is always the caller's explicit choice — there is no auto-merge —
mirroring the persistence package. ``checkout`` switches git files only; bringing
a version into the live model is the separate, explicit :meth:`restore` step.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from pycadwork.document import Document
from pycadwork.persistence import (
    ModelReader,
    ModelWriter,
    SnapshotDiff,
    diff,
)
from pycadwork.versioning._codec import SnapshotCodec
from pycadwork.versioning._git import init_repository, open_repository
from pycadwork.versioning._repository import (
    CommitInfo,
    Repository,
    RepositoryError,
    RepoStatus,
)


@dataclass(frozen=True, slots=True)
class CommitReport:
    """The outcome of a :meth:`ModelVersioning.commit`.

    ``nothing_to_commit`` is ``True`` when the working tree already matched the
    last commit (an idempotent re-commit); ``commit`` then refers to that
    existing head. ``document_file`` is the basename of the ``.3dc`` recorded in
    the manifest.
    """

    commit: CommitInfo
    files_changed: int
    nothing_to_commit: bool
    document_file: str


@dataclass(frozen=True, slots=True)
class RestoreReport:
    """The outcome of a :meth:`ModelVersioning.restore`.

    ``document_path`` is the working-tree ``.3dc`` to reopen in cadwork — the
    full-fidelity, primary restore. ``applied_to_model`` is ``True`` only when
    ``apply_to_model=True`` ran the best-effort JSON write-back; the four counts
    are then the :class:`~pycadwork.persistence.WriteResult` passthrough.
    """

    document_path: Path
    applied_to_model: bool
    created: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0


class ModelVersioning:
    """Bridge the live model to a git :class:`Repository` of JSONL + ``.3dc``."""

    __slots__ = ("_repo", "_codec", "_reader", "_writer")

    def __init__(
        self,
        repo: Repository,
        *,
        codec: SnapshotCodec | None = None,
        reader: ModelReader | None = None,
        writer: ModelWriter | None = None,
    ) -> None:
        self._repo = repo
        self._codec = codec or SnapshotCodec()
        self._reader = reader or ModelReader()
        self._writer = writer or ModelWriter()

    @classmethod
    def open(
        cls,
        root: Path | None = None,
        *,
        init: bool = True,
        repo: Repository | None = None,
    ) -> ModelVersioning:
        """Open a versioning bridge over a repository.

        * ``repo`` given → use it verbatim (the test / advanced path).
        * else ``root`` given → ``init_repository`` (default) or
          ``open_repository`` there.
        * else ``root=None`` → the repository lives in the active 3d file's
          directory; refuse if the model is unsaved (no path to anchor on). The
          only requirement is that the model has been saved to disk — the file
          type (``.3dc`` or otherwise) does not matter.
        """
        if repo is None:
            if root is None:
                file_path = Document().file_path
                if not file_path:
                    raise RepositoryError(
                        "the active model is unsaved, so there is no directory to "
                        "host the repository; save the 3d file first or pass an "
                        "explicit root="
                    )
                root = Path(file_path).parent
            root = Path(root)
            repo = init_repository(root) if init else open_repository(root)
        return cls(repo)

    @property
    def repository(self) -> Repository:
        """The underlying repository (for advanced / direct git access)."""
        return self._repo

    # ---- model -> repo ----

    def commit(self, message: str, *, include_binary: bool = True) -> CommitReport:
        """Capture the model into the repository and commit it.

        Saves the ``.3dc``, writes the JSONL tree + (optionally) the binary, then
        commits. A second identical commit short-circuits to
        ``nothing_to_commit`` via :meth:`Repository.is_dirty`.
        """
        document = Document()
        document.save()
        document_file = Path(document.file_name).name

        snapshot = self._reader.read()
        paths = self._codec.write(
            snapshot, self._repo.working_dir, document_file=document_file
        )

        if include_binary:
            binary = self._copy_binary(document, document_file)
            if binary is not None:
                paths.append(binary)
                # Track the binary's actual extension, so any 3d file type (not
                # only .3dc) is committed through LFS.
                self._repo.ensure_lfs_tracked((_lfs_pattern(document_file),))

        gitattributes = self._repo.working_dir / ".gitattributes"
        if gitattributes.exists():
            paths.append(gitattributes)

        self._repo.stage(paths)

        if not self._repo.is_dirty():
            head = self._repo.log(max_count=1)
            existing = head[0] if head else _EMPTY_COMMIT
            return CommitReport(existing, 0, True, document_file)

        status = self._repo.status()
        files_changed = len(status.untracked) + len(status.modified)
        info = self._repo.commit(message)
        return CommitReport(info, files_changed, False, document_file)

    def _copy_binary(self, document: Document, document_file: str) -> Path | None:
        """Copy the saved ``.3dc`` into the working tree; return its tracked path.

        Returns ``None`` if the model has no on-disk file yet (unsaved): the
        commit then carries JSONL only. When the working tree already *is* the
        ``.3dc``'s directory the copy is a no-op but the path is still tracked.
        """
        source_str = document.file_path
        if not source_str:
            return None
        source = Path(source_str)
        if not source.is_file():
            return None
        dest = self._repo.working_dir / document_file
        if source.resolve() != dest.resolve():
            shutil.copyfile(source, dest)
        return dest

    # ---- repo -> model / user ----

    def restore(self, *, apply_to_model: bool = False) -> RestoreReport:
        """Resolve the working-tree ``.3dc`` to reopen; optionally write JSON back.

        The returned ``document_path`` is always the full-fidelity restore. With
        ``apply_to_model=True`` the JSON snapshot is *additionally* applied to the
        live model (best-effort — see the package limitations).
        """
        manifest = self._codec.read_manifest(self._repo.working_dir)
        document_path = self._repo.working_dir / manifest.document_file

        if not apply_to_model:
            return RestoreReport(document_path, applied_to_model=False)

        current = self._reader.read()
        target = self._codec.read(self._repo.working_dir)
        result = self._writer.apply(diff(current, target))
        return RestoreReport(
            document_path,
            applied_to_model=True,
            created=result.created,
            updated=result.updated,
            deleted=result.deleted,
            skipped=result.skipped,
        )

    load = restore

    def model_status(self) -> SnapshotDiff:
        """Preview: diff the live model against the working-tree snapshot (no git)."""
        current = self._reader.read()
        target = self._codec.read(self._repo.working_dir)
        return diff(current, target)

    # ---- pure git passthrough ----

    def create_branch(self, name: str, *, checkout: bool = True) -> None:
        self._repo.create_branch(name, checkout=checkout)

    def delete_branch(self, name: str, *, force: bool = False) -> None:
        """Delete local branch ``name`` (``force`` discards unmerged commits)."""
        self._repo.delete_branch(name, force=force)

    def checkout(self, ref: str) -> None:
        """Switch git files to ``ref``; call :meth:`restore` / :meth:`load` after."""
        self._repo.checkout(ref)

    def merge(self, ref: str, *, ff_only: bool = False) -> None:
        """Merge ``ref`` into the current branch (ordinary git, no auto-resolve).

        ``ff_only`` refuses a non-fast-forward; conflicts raise
        :class:`MergeConflictError`. The merged ``.3dc`` is restored to the working
        tree — call :meth:`restore` to reopen it (or :meth:`restore`
        ``(apply_to_model=True)`` to bring it into the live model).
        """
        self._repo.merge(ref, ff_only=ff_only)

    def diff(
        self, a: str | None = None, b: str | None = None, *, stat: bool = False
    ) -> str:
        """The textual diff of the JSONL tree — the reviewable payoff of versioning.

        No refs: working tree vs ``HEAD``. ``a`` only: ``a`` vs working tree. Both:
        ``a`` vs ``b``. ``stat=True`` returns the per-file summary.
        """
        return self._repo.diff(a, b, stat=stat)

    def branches(self) -> tuple[str, ...]:
        return self._repo.branches()

    def current_branch(self) -> str:
        return self._repo.current_branch()

    def remotes(self) -> tuple[str, ...]:
        """Every configured remote name."""
        return self._repo.remotes()

    def add_remote(self, name: str, url: str) -> None:
        """Point remote ``name`` at ``url`` (idempotent — updates an existing one)."""
        self._repo.add_remote(name, url)

    def push(
        self, remote: str = "origin", ref: str | None = None, *, force: bool = False
    ) -> None:
        """Push ``ref`` (default: current branch) to ``remote``; ``force`` overwrites."""
        self._repo.push(remote, ref, force=force)

    def pull(self, remote: str = "origin", ref: str | None = None) -> None:
        """Pull ``ref`` from ``remote``; :class:`MergeConflictError` is surfaced."""
        self._repo.pull(remote, ref)

    def log(self, max_count: int = 50) -> tuple[CommitInfo, ...]:
        return self._repo.log(max_count=max_count)

    def status(self) -> RepoStatus:
        return self._repo.status()


def _lfs_pattern(document_file: str) -> str:
    """The LFS glob for the binary's extension (e.g. ``*.3dc``, ``*.3d``).

    Falls back to the literal filename if it has no extension, so the committed
    binary is always tracked regardless of the 3d file type.
    """
    suffix = Path(document_file).suffix
    return f"*{suffix}" if suffix else document_file


#: A placeholder returned only in the (unreachable in practice) case of a
#: ``nothing_to_commit`` on a repository with no commits at all.
_EMPTY_COMMIT = CommitInfo(sha="", message="", author="", committed_at="")

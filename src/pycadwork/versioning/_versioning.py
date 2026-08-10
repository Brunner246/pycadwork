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
* :meth:`reload_model` brings a version fully **back into the live model**. By
  default (``strategy="smart"``) it reconciles the live model against the
  target by content fingerprint (see :mod:`pycadwork.versioning._sync`):
  elements that did not change keep their existing cadwork id/GUID untouched,
  only the true delta is added/removed, and a pure-removal switch never even
  touches the binary. ``strategy="full"`` reproduces the original behavior —
  every live element is deleted and the whole committed ``.3dc`` is imported
  through the ``file_controller`` seam, so *every* element gets a fresh cadwork
  id/GUID regardless of whether it changed. Either way the restore is
  full-fidelity — real geometry for every element type, including element
  moves. **Project-level metadata is not carried by the binary import** (only
  the JSON write-back below carries it). :meth:`switch_to` is the one-shot
  ``checkout`` + ``reload_model``.
* :meth:`restore` (alias :meth:`load`) is the lower-level form: it returns the
  working-tree ``.3dc`` path (e.g. to reopen by hand on another machine), and
  ``apply_to_model=True`` additionally runs the *legacy, best-effort* JSON
  write-back through ``ModelWriter`` (existing points are never moved,
  non-reconstructable types are skipped — see the package docstring). It carries
  project metadata the binary reload cannot, but cannot reproduce element moves.

Direction is always the caller's explicit choice — there is no auto-merge —
mirroring the persistence package. ``checkout`` switches git files only; bringing
a version into the live model is the separate, explicit :meth:`reload_model`
step (or :meth:`switch_to`, which combines them).
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pycadwork.document import Document
from pycadwork.persistence import (
    ModelReader,
    ModelSnapshot,
    ModelWriter,
    SnapshotDiff,
    diff,
)
from pycadwork.versioning._codec import MANIFEST_FILE, MODEL_DIR, SnapshotCodec
from pycadwork.versioning._git import init_repository, open_repository
from pycadwork.versioning._repository import (
    CommitInfo,
    Repository,
    RepositoryError,
    RepoStatus,
)
from pycadwork.versioning._sync import SyncPlan, classify

#: The ``.gitignore`` written into every repository the facade manages.
#:
#: The repository is hosted in the cadwork model's *own* directory (see
#: :meth:`ModelVersioning.open`), so the live ``.3d`` / ``.3dc`` that cadwork holds
#: open — plus any sidecars cadwork drops next to it — sit at the working-tree
#: root. Tracking the open file in place is fatal on Windows: a ``checkout`` to
#: another branch must *unlink* it to swap in that branch's version, and Windows
#: refuses to unlink a file another process has open. So we ignore everything at
#: the root by default and re-include only the versioned artifacts: the manifest
#: and the ``model/`` tree (the JSONL *and* the committed ``.3dc`` copy live
#: there). A checkout then only ever rewrites files under ``model/`` — never the
#: file cadwork has open — and an unsaved live edit never dirties ``status`` or
#: defeats the ``nothing_to_commit`` short-circuit.
_GITIGNORE = """\
# Managed by pycadwork.versioning — do not edit.
# The repo lives in the cadwork model's directory; track only the versioned
# snapshot (manifest + model/) and ignore the live model file and its sidecars,
# so a checkout never has to overwrite the file cadwork holds open.
/*
!/.gitignore
!/.gitattributes
!/manifest.json
!/model/
"""


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

    ``document_path`` is the working-tree ``.3dc``. ``applied_to_model`` is
    ``True`` only when ``apply_to_model=True`` ran the best-effort JSON
    write-back; the four counts are then the
    :class:`~pycadwork.persistence.WriteResult` passthrough. The JSON write-back
    is *legacy and lossy* — it never moves existing elements and skips
    non-reconstructable types; to bring a version fully into the live model use
    :meth:`ModelVersioning.reload_model` instead, which reloads the binary.
    """

    document_path: Path
    applied_to_model: bool
    created: int = 0
    updated: int = 0
    deleted: int = 0
    skipped: int = 0


@dataclass(frozen=True, slots=True)
class ReloadReport:
    """The outcome of a :meth:`ModelVersioning.reload_model` / :meth:`switch_to`.

    ``document_path`` is the committed ``.3dc`` that was loaded into the live
    model; ``imported`` is how many identifiable elements the model holds
    afterwards (the imported set, since the model is emptied first). This is the
    full-fidelity restore — real geometry for every element type, including moves
    the JSON write-back could not reproduce. Note the imported elements receive
    fresh cadwork ids/GUIDs, and project-level metadata (name/number/…) is *not*
    carried by the binary import (see the module docstring).
    """

    document_path: Path
    imported: int


@dataclass(frozen=True, slots=True)
class SmartSwitchReport:
    """The outcome of a smart-strategy :meth:`ModelVersioning.reload_model` / :meth:`switch_to`.

    ``document_path`` is the committed ``.3dc`` the sync was reconciled
    against. ``unchanged`` elements kept their existing cadwork id/GUID —
    never touched. ``added`` is how many new elements were actually brought in
    (after filtering out duplicates of what stayed unchanged); ``removed`` is
    how many stale elements were deleted. ``total`` is ``unchanged + added``,
    the model's element count afterwards. Unlike :class:`ReloadReport`, a
    smart switch never reassigns ids/GUIDs to elements that did not change —
    see the module docstring's sync algorithm and the container-atomicity
    limitation in docs/versioning.md.
    """

    document_path: Path
    unchanged: int
    added: int
    removed: int
    total: int


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

        # Keep the live, cadwork-open model file out of git so a later checkout
        # never has to overwrite it (which Windows forbids while it is open).
        paths.append(self._ensure_gitignore())

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
        """Copy the saved ``.3dc`` into the ``model/`` tree; return its tracked path.

        Returns ``None`` if the model has no on-disk file yet (unsaved): the
        commit then carries JSONL only. The copy lands under ``model/`` — *never*
        at the working-tree root next to the live file — so it is a distinct file
        from the one cadwork holds open: a checkout swaps this copy, leaving the
        open file untouched (see :data:`_GITIGNORE`).
        """
        source_str = document.file_path
        if not source_str:
            return None
        source = Path(source_str)
        if not source.is_file():
            return None
        dest = self._repo.working_dir / MODEL_DIR / document_file
        dest.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() != dest.resolve():
            shutil.copyfile(source, dest)
        return dest

    def _ensure_gitignore(self) -> Path:
        """Write the managed ``.gitignore`` (idempotently); return its path."""
        path = self._repo.working_dir / ".gitignore"
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != _GITIGNORE:
            path.write_text(_GITIGNORE, encoding="utf-8")
        return path

    # ---- repo -> model / user ----

    def restore(self, *, apply_to_model: bool = False) -> RestoreReport:
        """Resolve the working-tree ``.3dc`` path; optionally write JSON back.

        The returned ``document_path`` is the committed ``.3dc`` (e.g. to reopen
        by hand). With ``apply_to_model=True`` the JSON snapshot is *additionally*
        applied to the live model — legacy best-effort: it never moves existing
        elements and skips non-reconstructable types (see the package
        limitations). To bring a version fully into the live model, prefer
        :meth:`reload_model`.
        """
        manifest = self._codec.read_manifest(self._repo.working_dir)
        document_path = self._repo.working_dir / MODEL_DIR / manifest.document_file

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

    def reload_model(
        self, *, strategy: Literal["smart", "full"] = "smart"
    ) -> ReloadReport | SmartSwitchReport:
        """Load the committed ``.3dc`` into the live model.

        Reads the working tree's manifest for the tracked binary. With the
        default ``strategy="smart"``, the live model is reconciled against the
        working-tree snapshot by content fingerprint (see
        :func:`pycadwork.versioning._sync.classify`): elements that did not
        change keep their existing cadwork id/GUID untouched, only the true
        delta is added/removed, and a pure-removal switch never even imports
        the binary. Returns a :class:`SmartSwitchReport`.

        ``strategy="full"`` reproduces the original, simpler behavior verbatim:
        :meth:`pycadwork.document.Document.reload_from` deletes *every* live
        element and imports the binary, so every element gets a fresh id/GUID
        regardless of whether it changed. Returns a :class:`ReloadReport`. Use
        this escape hatch when a clean id/GUID reset is actually what you want.

        Pair with :meth:`checkout` (or use :meth:`switch_to`) to load a
        *specific* version: checkout swaps the tracked ``.3dc`` on disk, this
        loads it into cadwork.

        Raises :class:`RepositoryError` if the commit carries no binary (e.g. it
        was made with ``include_binary=False``, so the manifest names no file or
        the file is absent) — there is then nothing full-fidelity to reload.
        """
        document_path = self._resolve_document_path()

        if strategy == "full":
            imported = Document().reload_from(document_path)
            return ReloadReport(document_path, imported=imported)

        current = self._reader.read()
        target = self._codec.read(self._repo.working_dir)
        plan = classify(current, target)
        added = Document().apply_sync(plan, document_path)
        return SmartSwitchReport(
            document_path=document_path,
            unchanged=len(plan.unchanged),
            added=added,
            removed=len(plan.stale),
            total=len(plan.unchanged) + added,
        )

    def _resolve_document_path(self) -> Path:
        manifest = self._codec.read_manifest(self._repo.working_dir)
        if not manifest.document_file:
            raise RepositoryError(
                "this version has no committed .3dc to reload (it was committed "
                "without the binary); use restore(apply_to_model=True) for the "
                "best-effort JSON write-back instead"
            )
        document_path = self._repo.working_dir / MODEL_DIR / manifest.document_file
        if not document_path.is_file():
            raise RepositoryError(
                f"the committed model file is missing at {document_path} "
                "(an LFS pointer that was never smudged, or a stripped binary); "
                "cannot reload it into the model"
            )
        return document_path

    def switch_to(
        self, ref: str, *, strategy: Literal["smart", "full"] = "smart"
    ) -> ReloadReport | SmartSwitchReport:
        """Check out ``ref`` and load its committed model — git checkout, fully.

        The one-shot equivalent of :meth:`checkout` followed by
        :meth:`reload_model`: it switches the tracked files to ``ref`` and brings
        that version into the live cadwork model in a single step. ``strategy``
        is passed straight through to :meth:`reload_model` — see there for the
        smart-vs-full distinction. Even the default ``strategy="smart"`` can
        still touch elements that changed on either side, so a caller with
        unsaved live edits should confirm first.
        """
        self.checkout(ref)
        return self.reload_model(strategy=strategy)

    def model_status(self) -> SnapshotDiff:
        """Preview: diff the live model against the working-tree snapshot (no git)."""
        current = self._reader.read()
        target = self._codec.read(self._repo.working_dir)
        return diff(current, target)

    def sync_status(self) -> SyncPlan:
        """Preview: classify the live model against the working-tree snapshot (no git).

        The smart-switch analogue of :meth:`model_status`: shows what a
        ``reload_model(strategy="smart")`` would do against the *currently
        checked-out* version without touching anything.
        """
        current = self._reader.read()
        target = self._codec.read(self._repo.working_dir)
        return classify(current, target)

    def preview_switch(self, ref: str) -> SyncPlan:
        """Preview a smart :meth:`switch_to` to ``ref`` before checking it out.

        A true *pre-checkout* preview: it reads ``ref``'s committed JSONL
        straight out of git (via :meth:`Repository.read_file_at_ref`, one file
        at a time) without switching any tracked files on disk, then classifies
        the live model against it exactly like :meth:`sync_status` does for the
        checked-out version.
        """
        current = self._reader.read()
        target = self._read_snapshot_at_ref(ref)
        return classify(current, target)

    def _read_snapshot_at_ref(self, ref: str) -> ModelSnapshot:
        manifest_text = self._repo.read_file_at_ref(ref, MANIFEST_FILE)
        table_texts: dict[str, str] = {}
        for filename in self._codec.table_filenames():
            try:
                table_texts[filename] = self._repo.read_file_at_ref(
                    ref, f"{MODEL_DIR}/{filename}"
                )
            except RepositoryError:
                table_texts[filename] = ""
        return self._codec.read_texts(manifest_text, table_texts)

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

    def ensure_local_remote(self, path: Path | str, name: str = "origin") -> str:
        """Wire remote ``name`` to a local bare repository at ``path``; return ``name``.

        Initializes a bare repository at ``path`` if one is not already there
        (idempotent), then points ``name`` at it. ``path`` is any local filesystem
        location — a plain folder or a UNC network share — so :meth:`push` and
        :meth:`pull` run entirely over the filesystem with **no network server**.
        Use this to version a model locally (no GitHub/GitLab); use
        :meth:`add_remote` for an ordinary server URL.
        """
        target = self._repo.init_local_remote(Path(path))
        self._repo.add_remote(name, str(target))
        return name

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

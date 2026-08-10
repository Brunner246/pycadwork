"""GitRepository — the concrete :class:`Repository` over GitPython.

GitPython (and the ``git`` executable it drives) is the heavy, often-absent
dependency: cadwork's embedded Python usually ships neither. So this module
imports ``git`` **lazily inside methods only** — never at module top level —
exactly like the cwapi3d controllers and
:class:`pycadwork.persistence.SqliteConnection`. Importing
:mod:`pycadwork.versioning` therefore never pulls in GitPython; the first git
*operation* is where a precise :class:`GitNotAvailableError` is raised (with the
fix: install ``pycadwork[git]`` / put ``git`` on PATH).

The CLI surface (``repo.git.add`` / ``commit`` / ``checkout`` / ``push`` / …) is
used for mutating operations so the git-lfs clean/smudge filters actually run;
the object API (``iter_commits`` / ``heads`` / ``is_dirty``) is used for reads.

**Git LFS is degrade-and-warn:** :func:`init_repository` installs LFS and tracks
``*.3d`` / ``*.3dc`` (a cadwork model may be saved as either) when ``git-lfs`` is
present; when it is absent it warns once and the
binary commits as an ordinary (large) blob — the repo is still valid, only
heavier. Pushing/pulling an LFS history on an LFS-less machine errors from git
itself, surfaced as :class:`RepositoryError`.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import warnings
from collections.abc import Sequence
from datetime import timezone
from pathlib import Path
from typing import Any

from pycadwork.versioning._repository import (
    CommitInfo,
    GitNotAvailableError,
    MergeConflictError,
    NoRepositoryError,
    RepoStatus,
    RepositoryError,
)

#: The .gitattributes line that routes a pattern through git-lfs as binary.
_LFS_ATTRIBUTE = "filter=lfs diff=lfs merge=lfs -text"

#: Patterns the versioning facade tracks with LFS by default. A cadwork model
#: may be saved as either ``.3d`` or ``.3dc``, so both globs are tracked up
#: front; :func:`pycadwork.versioning._versioning._lfs_pattern` additionally
#: tracks the live document's actual extension at commit time.
DEFAULT_LFS_PATTERNS: tuple[str, ...] = ("*.3d", "*.3dc")


def is_git_available() -> bool:
    """True iff GitPython is importable *and* a ``git`` executable is on PATH."""
    if importlib.util.find_spec("git") is None:
        return False
    return shutil.which("git") is not None


def is_lfs_available() -> bool:
    """True iff ``git lfs`` runs (git-lfs installed and on PATH)."""
    git_exe = shutil.which("git")
    if git_exe is None:
        return False
    try:
        subprocess.run(
            [git_exe, "lfs", "version"],
            capture_output=True,
            check=True,
        )
        return True
    except OSError, subprocess.CalledProcessError:
        return False


def _import_git() -> Any:
    """Import GitPython or raise a precise :class:`GitNotAvailableError`."""
    if importlib.util.find_spec("git") is None:
        raise GitNotAvailableError(
            "GitPython is not installed — install the optional extra: "
            "pip install 'pycadwork[git]'"
        )
    if shutil.which("git") is None:
        raise GitNotAvailableError(
            "no `git` executable on PATH — cadwork's embedded Python usually "
            "lacks one; install git or run versioning from a host Python"
        )
    import git

    return git


def open_repository(root: Path) -> GitRepository:
    """Open the existing git repository at ``root``.

    Raises :class:`NoRepositoryError` if ``root`` is not (inside) a repository,
    or :class:`GitNotAvailableError` if git/GitPython are unavailable.
    """
    git = _import_git()
    try:
        repo = git.Repo(Path(root))
    except (git.InvalidGitRepositoryError, git.NoSuchPathError) as exc:
        raise NoRepositoryError(f"no git repository at {root}") from exc
    return GitRepository(repo)


def init_repository(root: Path) -> GitRepository:
    """Initialize a git repository at ``root`` (idempotent) and set up LFS.

    When ``git-lfs`` is available, runs ``git lfs install --local`` and tracks
    ``*.3d`` / ``*.3dc``; otherwise warns once and continues without LFS.
    """
    git = _import_git()
    path = Path(root)
    path.mkdir(parents=True, exist_ok=True)
    repo = git.Repo.init(path)
    repository = GitRepository(repo)

    if is_lfs_available():
        try:
            repo.git.lfs("install", "--local")
        except git.GitCommandError as exc:  # pragma: no cover - environment-specific
            raise RepositoryError(f"git lfs install failed: {exc}") from exc
        repository.ensure_lfs_tracked(DEFAULT_LFS_PATTERNS)
    else:
        _warn_no_lfs()
    return repository


def init_bare_repository(path: Path) -> Path:
    """Initialize a **bare** repository at ``path`` (idempotent); return ``path``.

    A bare repo has no working tree, so it is a valid *remote* but not a
    :class:`GitRepository`. Used to wire a self-contained, network-free
    ``origin`` for examples / tests — in real use you ``add_remote`` an existing
    server URL instead.
    """
    git = _import_git()
    target = Path(path)
    if not (target / "HEAD").exists():
        git.Repo.init(target, bare=True)
    return target


def _warn_no_lfs() -> None:
    warnings.warn(
        "git-lfs is not installed; binary .3d/.3dc files will be committed as "
        "ordinary git blobs (the repository works but grows large). Install "
        "git-lfs for efficient binary versioning.",
        RuntimeWarning,
        stacklevel=2,
    )


class GitRepository:
    """A :class:`~pycadwork.versioning.Repository` backed by a GitPython repo."""

    __slots__ = ("_repo", "_lfs_warned")

    def __init__(self, repo: Any) -> None:
        self._repo = repo
        self._lfs_warned = False

    # ---- helpers ----

    def _git_error(self) -> type[Exception]:
        import git

        return git.GitCommandError

    def _commit_info(self, commit: Any) -> CommitInfo:
        committed = commit.committed_datetime.astimezone(timezone.utc).isoformat()
        return CommitInfo(
            sha=commit.hexsha,
            message=commit.message.rstrip("\n"),
            author=f"{commit.author.name} <{commit.author.email}>",
            committed_at=committed,
        )

    # ---- Repository surface ----

    @property
    def working_dir(self) -> Path:
        return Path(self._repo.working_tree_dir)

    def stage(self, paths: Sequence[Path]) -> None:
        existing = [str(Path(p)) for p in paths if Path(p).exists()]
        if not existing:
            return
        try:
            self._repo.git.add("--", *existing)
        except self._git_error() as exc:
            raise RepositoryError(f"git add failed: {exc}") from exc

    def commit(self, message: str) -> CommitInfo:
        try:
            self._repo.git.commit("-m", message)
        except self._git_error() as exc:
            raise RepositoryError(f"git commit failed: {exc}") from exc
        return self._commit_info(self._repo.head.commit)

    def current_branch(self) -> str:
        try:
            return self._repo.active_branch.name
        except TypeError:
            # Detached HEAD — no branch; report the short sha.
            return self._repo.head.commit.hexsha[:12]

    def branches(self) -> tuple[str, ...]:
        return tuple(head.name for head in self._repo.heads)

    def create_branch(self, name: str, *, checkout: bool = True) -> None:
        try:
            if checkout:
                self._repo.git.checkout("-b", name)
            else:
                self._repo.create_head(name)
        except self._git_error() as exc:
            raise RepositoryError(f"creating branch {name!r} failed: {exc}") from exc

    def delete_branch(self, name: str, *, force: bool = False) -> None:
        flag = "-D" if force else "-d"
        try:
            self._repo.git.branch(flag, name)
        except self._git_error() as exc:
            raise RepositoryError(f"deleting branch {name!r} failed: {exc}") from exc

    def checkout(self, ref: str) -> None:
        try:
            self._repo.git.checkout(ref)
        except self._git_error() as exc:
            raise RepositoryError(f"checkout of {ref!r} failed: {exc}") from exc

    def merge(self, ref: str, *, ff_only: bool = False) -> None:
        args = ["--ff-only", ref] if ff_only else [ref]
        try:
            self._repo.git.merge(*args)
        except self._git_error() as exc:
            if "conflict" in str(exc).lower():
                raise MergeConflictError(
                    f"merge of {ref!r} produced conflicts; resolve in git, then "
                    "restore()/reopen"
                ) from exc
            raise RepositoryError(f"merge of {ref!r} failed: {exc}") from exc
        if self._repo.index.unmerged_blobs():
            raise MergeConflictError(
                f"merge of {ref!r} produced conflicts; resolve in git"
            )

    def read_file_at_ref(self, ref: str, path: str) -> str:
        try:
            return self._repo.git.show(f"{ref}:{path}")
        except self._git_error() as exc:
            raise RepositoryError(f"reading {path!r} at {ref!r} failed: {exc}") from exc

    def diff(
        self, a: str | None = None, b: str | None = None, *, stat: bool = False
    ) -> str:
        args = ["--stat"] if stat else []
        if a is not None:
            args.append(a)
        if b is not None:
            args.append(b)
        try:
            return self._repo.git.diff(*args)
        except self._git_error() as exc:
            raise RepositoryError(f"git diff failed: {exc}") from exc

    def remotes(self) -> tuple[str, ...]:
        return tuple(remote.name for remote in self._repo.remotes)

    def add_remote(self, name: str, url: str) -> None:
        try:
            if name in self.remotes():
                self._repo.git.remote("set-url", name, url)
            else:
                self._repo.git.remote("add", name, url)
        except self._git_error() as exc:
            raise RepositoryError(f"configuring remote {name!r} failed: {exc}") from exc

    def init_local_remote(self, path: Path) -> Path:
        return init_bare_repository(path)

    def push(
        self, remote: str = "origin", ref: str | None = None, *, force: bool = False
    ) -> None:
        target = ref or self.current_branch()
        args = ["--force", remote, target] if force else [remote, target]
        try:
            self._repo.git.push(*args)
        except self._git_error() as exc:
            raise RepositoryError(f"push to {remote}/{target} failed: {exc}") from exc

    def pull(self, remote: str = "origin", ref: str | None = None) -> None:
        target = ref or self.current_branch()
        try:
            self._repo.git.pull(remote, target)
        except self._git_error() as exc:
            if "conflict" in str(exc).lower():
                raise MergeConflictError(
                    f"pull from {remote}/{target} produced conflicts; resolve in "
                    "git, then restore()/reopen"
                ) from exc
            raise RepositoryError(f"pull from {remote}/{target} failed: {exc}") from exc
        if self._repo.index.unmerged_blobs():
            raise MergeConflictError(
                f"pull from {remote}/{target} produced conflicts; resolve in git"
            )

    def fetch(self, remote: str = "origin") -> None:
        try:
            self._repo.git.fetch(remote)
        except self._git_error() as exc:
            raise RepositoryError(f"fetch from {remote} failed: {exc}") from exc

    def log(self, max_count: int = 50) -> tuple[CommitInfo, ...]:
        try:
            commits = self._repo.iter_commits(max_count=max_count)
            return tuple(self._commit_info(c) for c in commits)
        except ValueError, self._git_error():
            # No commits yet (unborn branch).
            return ()

    def status(self) -> RepoStatus:
        modified = tuple(sorted(d.a_path for d in self._repo.index.diff(None)))
        untracked = tuple(sorted(self._repo.untracked_files))
        return RepoStatus(
            branch=self.current_branch(),
            is_dirty=self.is_dirty(),
            untracked=untracked,
            modified=modified,
        )

    def is_dirty(self) -> bool:
        return self._repo.is_dirty(untracked_files=True)

    def ensure_lfs_attributes(self, patterns: Sequence[str]) -> None:
        path = self.working_dir / ".gitattributes"
        existing = (
            path.read_text(encoding="utf-8").splitlines() if path.exists() else []
        )
        present = {line.split(maxsplit=1)[0] for line in existing if line.strip()}
        added = [f"{p} {_LFS_ATTRIBUTE}" for p in patterns if p not in present]
        if not added:
            return
        lines = existing + added
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def ensure_lfs_tracked(self, patterns: Sequence[str]) -> None:
        if not is_lfs_available():
            if not self._lfs_warned:
                _warn_no_lfs()
                self._lfs_warned = True
            return
        for pattern in patterns:
            try:
                self._repo.git.lfs("track", pattern)
            except self._git_error() as exc:
                raise RepositoryError(
                    f"git lfs track {pattern!r} failed: {exc}"
                ) from exc

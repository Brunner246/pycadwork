"""The git seam — a narrow :class:`Repository` Protocol plus its value types.

This is the versioning analogue of
:class:`pycadwork.persistence.GatewayConnection`: a small, explicit port the
facade talks to, with a concrete GitPython implementation
(:class:`pycadwork.versioning._git.GitRepository`) and an in-memory
:class:`~tests._fakes.repository.FakeRepository` behind it. Keeping the surface
this narrow means the facade is testable with no git executable, and a future
backend (libgit2, a hosted API) only has to satisfy this one Protocol.

Only the operations the facade actually needs are exposed; the direction of
every operation is the caller's explicit choice (no auto-merge), mirroring the
persistence package's philosophy. The two value types are frozen so a
:class:`CommitInfo` / :class:`RepoStatus` returned from a method cannot be
mutated by a caller.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CommitInfo:
    """One commit's identity and metadata.

    ``committed_at`` is an ISO-8601 UTC timestamp string — kept as text so the
    value type stays purely data and serializes trivially.
    """

    sha: str
    message: str
    author: str
    committed_at: str


@dataclass(frozen=True, slots=True)
class RepoStatus:
    """The working tree's branch and dirtiness at a point in time."""

    branch: str
    is_dirty: bool
    untracked: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()


class RepositoryError(RuntimeError):
    """Base class for every repository-seam failure."""


class GitNotAvailableError(RepositoryError):
    """GitPython is not installed, or no ``git`` executable is on PATH."""


class LfsNotAvailableError(RepositoryError):
    """``git-lfs`` is not installed where an LFS operation required it."""


class NoRepositoryError(RepositoryError):
    """No git repository exists at the requested path."""


class MergeConflictError(RepositoryError):
    """A pull/merge produced conflicts; surfaced, never auto-resolved."""


@runtime_checkable
class Repository(Protocol):
    """The narrow git port the versioning facade depends on.

    Implementations carry out each operation against a real or fake repository;
    the facade never reaches past this surface. ``checkout`` switches
    working-tree files only — bringing a version into the live cadwork model is a
    separate, explicit facade step.
    """

    @property
    def working_dir(self) -> Path:
        """The repository's working-tree root (where the JSONL tree lives)."""
        ...

    def stage(self, paths: Sequence[Path]) -> None:
        """Stage ``paths`` for the next commit (``git add``)."""
        ...

    def commit(self, message: str) -> CommitInfo:
        """Commit the staged changes with ``message``; return the new commit."""
        ...

    def current_branch(self) -> str:
        """The name of the checked-out branch."""
        ...

    def branches(self) -> tuple[str, ...]:
        """Every local branch name."""
        ...

    def create_branch(self, name: str, *, checkout: bool = True) -> None:
        """Create branch ``name``, optionally checking it out."""
        ...

    def delete_branch(self, name: str, *, force: bool = False) -> None:
        """Delete local branch ``name`` (``force`` discards unmerged commits)."""
        ...

    def checkout(self, ref: str) -> None:
        """Switch the working tree to ``ref`` (branch or commit)."""
        ...

    def merge(self, ref: str, *, ff_only: bool = False) -> None:
        """Merge ``ref`` into the current branch.

        ``ff_only`` refuses anything but a fast-forward. A merge that produces
        conflicts raises :class:`MergeConflictError`, never auto-resolves — the
        binary model file can't be line-merged, so the caller resolves in git
        and reopens.
        """
        ...

    def diff(
        self, a: str | None = None, b: str | None = None, *, stat: bool = False
    ) -> str:
        """Return the textual diff of the tracked files (the reviewable payoff).

        With no refs: working tree vs ``HEAD``. With ``a`` only: ``a`` vs working
        tree. With both: ``a`` vs ``b``. ``stat`` returns the ``--stat`` summary
        instead of the full per-line diff.
        """
        ...

    def remotes(self) -> tuple[str, ...]:
        """Every configured remote name."""
        ...

    def add_remote(self, name: str, url: str) -> None:
        """Configure remote ``name`` to point at ``url`` (idempotent: updates if it exists)."""
        ...

    def push(
        self, remote: str = "origin", ref: str | None = None, *, force: bool = False
    ) -> None:
        """Push ``ref`` (default: current branch) to ``remote``; ``force`` overwrites."""
        ...

    def pull(self, remote: str = "origin", ref: str | None = None) -> None:
        """Pull ``ref`` from ``remote``; raise :class:`MergeConflictError` on conflict."""
        ...

    def fetch(self, remote: str = "origin") -> None:
        """Fetch from ``remote`` without merging."""
        ...

    def log(self, max_count: int = 50) -> tuple[CommitInfo, ...]:
        """The most recent commits on the current branch, newest first."""
        ...

    def status(self) -> RepoStatus:
        """The current :class:`RepoStatus`."""
        ...

    def is_dirty(self) -> bool:
        """True if the working tree (or index) has uncommitted changes."""
        ...

    def ensure_lfs_attributes(self, patterns: Sequence[str]) -> None:
        """Write/merge ``.gitattributes`` so ``patterns`` are LFS-tracked text-off."""
        ...

    def ensure_lfs_tracked(self, patterns: Sequence[str]) -> None:
        """Register ``patterns`` with git-lfs (no-op on a non-LFS implementation)."""
        ...

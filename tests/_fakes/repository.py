"""In-memory fake of the :class:`~pycadwork.versioning.Repository` Protocol.

Real files live in a ``tmp_path`` working tree; the branch/commit graph is
in-memory. A commit captures the whole working tree as a content snapshot, and
``checkout`` restores the target commit's snapshot onto disk — so the full
commit → branch → checkout → restore loop runs with **no git executable**,
letting the versioning facade be tested anywhere.

It is importable by both the tests and ``examples/versioning.py`` (the example
demos the facade against it so the example stays CI-safe). Determinism is kept by
a per-instance counter for commit shas and timestamps — no wall-clock, so two
identical runs produce identical commit metadata.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pycadwork.versioning._repository import CommitInfo, RepoStatus

_DEFAULT_BRANCH = "main"
_AUTHOR = "Fake Author <fake@example.com>"


def _scan_tree(root: Path) -> dict[str, bytes]:
    """Every file under ``root`` as ``{posix-relative-path: bytes}``."""
    tree: dict[str, bytes] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            tree[path.relative_to(root).as_posix()] = path.read_bytes()
    return tree


@dataclass
class _Commit:
    info: CommitInfo
    parent: str | None
    tree: dict[str, bytes]


@dataclass
class FakeRepository:
    """A working-tree-backed, in-memory :class:`Repository` implementation."""

    root: Path
    _branch: str = _DEFAULT_BRANCH
    _branches: dict[str, str | None] = field(default_factory=dict)
    _commits: dict[str, _Commit] = field(default_factory=dict)
    _staged: set[str] = field(default_factory=set)
    _seq: int = 0
    _remotes: dict[str, str] = field(default_factory=dict)
    # observables for tests
    lfs_attribute_patterns: list[str] = field(default_factory=list)
    lfs_tracked_patterns: list[str] = field(default_factory=list)
    push_calls: list[tuple[str, str | None, bool]] = field(default_factory=list)
    pull_calls: list[tuple[str, str | None]] = field(default_factory=list)
    fetch_calls: list[str] = field(default_factory=list)
    merge_calls: list[tuple[str, bool]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.root = Path(self.root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._branches.setdefault(self._branch, None)

    # ---- helpers ----

    def _head_sha(self) -> str | None:
        return self._branches.get(self._branch)

    def _head_tree(self) -> dict[str, bytes]:
        sha = self._head_sha()
        return dict(self._commits[sha].tree) if sha is not None else {}

    def _next_sha(self) -> str:
        self._seq += 1
        return format(self._seq, "040x")

    def _next_timestamp(self) -> str:
        # Deterministic, monotonic, valid ISO-8601 UTC — no wall-clock.
        return f"2000-01-01T00:00:{self._seq:02d}+00:00"

    def _restore_tree(self, tree: dict[str, bytes]) -> None:
        for path in sorted(self.root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
        for rel, data in tree.items():
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    # ---- Repository surface ----

    @property
    def working_dir(self) -> Path:
        return self.root

    def stage(self, paths: Sequence[Path]) -> None:
        for path in paths:
            resolved = Path(path)
            rel = (
                resolved.relative_to(self.root) if resolved.is_absolute() else resolved
            )
            self._staged.add(rel.as_posix())

    def commit(self, message: str) -> CommitInfo:
        sha = self._next_sha()
        info = CommitInfo(
            sha=sha,
            message=message,
            author=_AUTHOR,
            committed_at=self._next_timestamp(),
        )
        self._commits[sha] = _Commit(
            info=info, parent=self._head_sha(), tree=_scan_tree(self.root)
        )
        self._branches[self._branch] = sha
        self._staged.clear()
        return info

    def current_branch(self) -> str:
        return self._branch

    def branches(self) -> tuple[str, ...]:
        return tuple(sorted(self._branches))

    def create_branch(self, name: str, *, checkout: bool = True) -> None:
        self._branches[name] = self._head_sha()
        if checkout:
            self._branch = name

    def delete_branch(self, name: str, *, force: bool = False) -> None:
        if name == self._branch:
            from pycadwork.versioning._repository import RepositoryError

            raise RepositoryError(f"cannot delete the checked-out branch {name!r}")
        self._branches.pop(name, None)

    def _is_ancestor(self, maybe_ancestor: str | None, descendant: str | None) -> bool:
        sha: str | None = descendant
        while sha is not None:
            if sha == maybe_ancestor:
                return True
            sha = self._commits[sha].parent
        return maybe_ancestor is None

    def merge(self, ref: str, *, ff_only: bool = False) -> None:
        from pycadwork.versioning._repository import RepositoryError

        target = self._branches.get(ref, ref)
        if target not in self._commits:
            raise RepositoryError(f"unknown ref {ref!r}")
        self.merge_calls.append((ref, ff_only))
        if self._is_ancestor(self._head_sha(), target):  # fast-forward
            self._branches[self._branch] = target
            self._restore_tree(dict(self._commits[target].tree))
            return
        if ff_only:
            raise RepositoryError(f"merge of {ref!r} is not a fast-forward")
        # Non-ff: record a merge commit that takes the merged tree (no conflict model).
        sha = self._next_sha()
        info = CommitInfo(
            sha=sha,
            message=f"Merge {ref}",
            author=_AUTHOR,
            committed_at=self._next_timestamp(),
        )
        self._commits[sha] = _Commit(
            info=info, parent=self._head_sha(), tree=dict(self._commits[target].tree)
        )
        self._branches[self._branch] = sha
        self._restore_tree(dict(self._commits[sha].tree))

    def diff(
        self, a: str | None = None, b: str | None = None, *, stat: bool = False
    ) -> str:
        def commit_tree(ref: str) -> dict[str, bytes]:
            sha = self._branches.get(ref, ref)
            return dict(self._commits[sha].tree) if sha in self._commits else {}

        # git semantics: no refs -> HEAD vs working tree; a only -> a vs working
        # tree; a and b -> a vs b.
        working = _scan_tree(self.root)
        if a is None:
            left, right = self._head_tree(), working
        elif b is None:
            left, right = commit_tree(a), working
        else:
            left, right = commit_tree(a), commit_tree(b)
        changed = [
            n for n in sorted(set(left) | set(right)) if left.get(n) != right.get(n)
        ]
        if stat:
            return "\n".join(f" {n} | changed" for n in changed)
        return "\n".join(f"--- a/{n}\n+++ b/{n}" for n in changed)

    def remotes(self) -> tuple[str, ...]:
        return tuple(sorted(self._remotes))

    def add_remote(self, name: str, url: str) -> None:
        self._remotes[name] = url

    def checkout(self, ref: str) -> None:
        if ref in self._branches:
            self._branch = ref
            sha = self._branches[ref]
        elif ref in self._commits:
            sha = ref
        else:
            from pycadwork.versioning._repository import RepositoryError

            raise RepositoryError(f"unknown ref {ref!r}")
        tree = dict(self._commits[sha].tree) if sha is not None else {}
        self._restore_tree(tree)

    def push(
        self, remote: str = "origin", ref: str | None = None, *, force: bool = False
    ) -> None:
        self.push_calls.append((remote, ref, force))

    def pull(self, remote: str = "origin", ref: str | None = None) -> None:
        self.pull_calls.append((remote, ref))

    def fetch(self, remote: str = "origin") -> None:
        self.fetch_calls.append(remote)

    def log(self, max_count: int = 50) -> tuple[CommitInfo, ...]:
        out: list[CommitInfo] = []
        sha = self._head_sha()
        while sha is not None and len(out) < max_count:
            commit = self._commits[sha]
            out.append(commit.info)
            sha = commit.parent
        return tuple(out)

    def status(self) -> RepoStatus:
        head = self._head_tree()
        current = _scan_tree(self.root)
        untracked = tuple(sorted(p for p in current if p not in head))
        modified = tuple(
            sorted(p for p in current if p in head and current[p] != head[p])
        )
        return RepoStatus(
            branch=self._branch,
            is_dirty=self.is_dirty(),
            untracked=untracked,
            modified=modified,
        )

    def is_dirty(self) -> bool:
        return _scan_tree(self.root) != self._head_tree()

    def ensure_lfs_attributes(self, patterns: Sequence[str]) -> None:
        for pattern in patterns:
            if pattern not in self.lfs_attribute_patterns:
                self.lfs_attribute_patterns.append(pattern)

    def ensure_lfs_tracked(self, patterns: Sequence[str]) -> None:
        self.ensure_lfs_attributes(patterns)
        for pattern in patterns:
            if pattern not in self.lfs_tracked_patterns:
                self.lfs_tracked_patterns.append(pattern)

"""pycadwork.versioning — a git workflow over a cadwork model.

A cadwork model is a binary ``.3d`` / ``.3dc`` that git can store but not *diff*. This
package adds a real git workflow — branch / checkout / commit / push / pull —
**plus** a machine-readable serialization so changes are reviewable. It is a thin
bridge between three already-existing pieces:

    model  ⇄  ModelSnapshot      (reuses pycadwork.persistence)
           ⇄  diffable JSONL     (SnapshotCodec — this package)
           ⇄  git                (Repository / GitRepository — GitPython behind a seam)

A :meth:`ModelVersioning.commit` losslessly captures the model as *both* a
deterministic per-table JSONL tree (the reviewable, line-diffable artifact) and
the saved ``.3d`` / ``.3dc`` tracked via Git LFS (the full-fidelity artifact a checkout
restores for reopening in cadwork). Branch / checkout / push / pull are ordinary
git.

**Honest limitations** (also in each docstring):

* ``commit`` is lossless; the optional JSON ``restore(apply_to_model=True)`` is
  *best-effort* — existing elements' points are never moved and
  non-reconstructable types are skipped. The binary ``.3dc`` is therefore the
  primary restore path; ``restore()`` returns its exact path to reopen.
* Float reads can drift across machines/cadwork builds → commit from a consistent
  environment to avoid spurious diffs.
* GitPython (extra ``pycadwork[git]``) and a ``git`` executable are required at
  runtime and are often absent inside cadwork — the import succeeds regardless;
  the first git *operation* raises a precise :class:`GitNotAvailableError`. Use
  :func:`is_git_available` to feature-detect. Git LFS is a further prerequisite
  for efficient binary versioning (degrade-and-warn without it).

Typical use::

    from pycadwork.versioning import ModelVersioning

    vcs = ModelVersioning.open()        # repo in the active .3dc's directory
    vcs.commit("framed the north wall")
    vcs.create_branch("alternative-roof")
    ...
    vcs.checkout("main")
    report = vcs.restore()              # report.document_path -> reopen in cadwork
"""

from __future__ import annotations

from pycadwork.versioning._codec import (
    FORMAT_VERSION,
    CodecError,
    Manifest,
    SnapshotCodec,
)
from pycadwork.versioning._git import (
    GitRepository,
    init_bare_repository,
    init_repository,
    is_git_available,
    is_lfs_available,
    open_repository,
)
from pycadwork.versioning._repository import (
    CommitInfo,
    GitNotAvailableError,
    LfsNotAvailableError,
    MergeConflictError,
    NoRepositoryError,
    Repository,
    RepositoryError,
    RepoStatus,
)
from pycadwork.versioning._sync import ElementFingerprint, SyncPlan, classify
from pycadwork.versioning._versioning import (
    CommitReport,
    ModelVersioning,
    ReloadReport,
    RestoreReport,
    SmartSwitchReport,
)

__all__ = [
    "FORMAT_VERSION",
    "CodecError",
    "CommitInfo",
    "CommitReport",
    "ElementFingerprint",
    "GitNotAvailableError",
    "GitRepository",
    "LfsNotAvailableError",
    "Manifest",
    "MergeConflictError",
    "ModelVersioning",
    "NoRepositoryError",
    "ReloadReport",
    "RepoStatus",
    "Repository",
    "RepositoryError",
    "RestoreReport",
    "SmartSwitchReport",
    "SnapshotCodec",
    "SyncPlan",
    "classify",
    "init_bare_repository",
    "init_repository",
    "is_git_available",
    "is_lfs_available",
    "open_repository",
]

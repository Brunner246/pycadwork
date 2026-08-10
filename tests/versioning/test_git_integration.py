"""Real-git integration tests for :class:`GitRepository` (skipped without git).

These exercise the GitPython backend against a real repository in ``tmp_path``.
They are skipped where no ``git`` executable / GitPython is present, so CI on a
git-less machine (e.g. inside cadwork) still passes. LFS-specific assertions are
additionally guarded by ``git lfs`` availability.

A deterministic identity is forced through the ``GIT_*`` environment so commits
succeed without relying on the machine's global git config.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.persistence.records import ElementRecord, ModelSnapshot, ProjectRecord
from pycadwork.versioning._codec import SnapshotCodec
from pycadwork.versioning._git import (
    GitRepository,
    init_repository,
    is_git_available,
    is_lfs_available,
    open_repository,
)
from pycadwork.versioning._repository import (
    NoRepositoryError,
    Repository,
    RepositoryError,
)

pytestmark = pytest.mark.skipif(
    not is_git_available(), reason="git executable / GitPython not available"
)


@pytest.fixture(autouse=True)
def _git_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in {
        "GIT_AUTHOR_NAME": "Test Bot",
        "GIT_AUTHOR_EMAIL": "bot@example.com",
        "GIT_COMMITTER_NAME": "Test Bot",
        "GIT_COMMITTER_EMAIL": "bot@example.com",
    }.items():
        monkeypatch.setenv(key, value)


def _snapshot(guid: str = "g") -> ModelSnapshot:
    return ModelSnapshot(
        project=ProjectRecord(guid, name="Tower"),
        elements=(ElementRecord(guid, 1, "beam", cadwork_guid="x"),),
    )


def _write_and_stage(repo: GitRepository, snapshot: ModelSnapshot) -> list[Path]:
    paths = SnapshotCodec().write(snapshot, repo.working_dir)
    # Stage the .gitattributes that `git lfs track` wrote at init too, so a
    # commit leaves a clean tree (mirrors what the facade stages).
    gitattributes = repo.working_dir / ".gitattributes"
    if gitattributes.exists():
        paths = [*paths, gitattributes]
    repo.stage(paths)
    return paths


def test_init_creates_a_repository(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    assert isinstance(repo, Repository)
    assert repo.working_dir == tmp_path
    assert (tmp_path / ".git").exists()


def test_open_missing_repository_raises(tmp_path: Path) -> None:
    with pytest.raises(NoRepositoryError):
        open_repository(tmp_path)


def test_commit_round_trips_through_log(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot())

    assert repo.is_dirty()
    info = repo.commit("initial snapshot")

    assert info.message == "initial snapshot"
    assert info.author == "Test Bot <bot@example.com>"
    assert not repo.is_dirty()
    assert [c.message for c in repo.log()] == ["initial snapshot"]


def test_branch_checkout_swaps_working_tree(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot("base"))
    repo.commit("base")
    assert repo.current_branch() in {"main", "master"}
    base_branch = repo.current_branch()

    repo.create_branch("feature", checkout=True)
    assert repo.current_branch() == "feature"
    _write_and_stage(repo, _snapshot("feature"))
    repo.commit("feature change")

    feature_guid = SnapshotCodec().read_manifest(repo.working_dir).project_guid
    assert feature_guid == "feature"

    repo.checkout(base_branch)
    base_guid = SnapshotCodec().read_manifest(repo.working_dir).project_guid
    assert base_guid == "base"

    assert set(repo.branches()) == {base_branch, "feature"}


def test_status_reports_clean_after_commit(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot())
    repo.commit("snap")
    status = repo.status()
    assert not status.is_dirty
    assert status.untracked == ()
    assert status.modified == ()


def test_reopen_sees_existing_history(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot())
    repo.commit("snap")

    reopened = open_repository(tmp_path)
    assert [c.message for c in reopened.log()] == ["snap"]


def test_delete_branch_removes_it(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot())
    repo.commit("base")
    base = repo.current_branch()

    repo.create_branch("scratch", checkout=False)
    assert "scratch" in repo.branches()
    repo.checkout(base)
    repo.delete_branch("scratch", force=True)
    assert "scratch" not in repo.branches()


def test_read_file_at_ref_reads_without_checking_out(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot("a"))
    first = repo.commit("first")
    _write_and_stage(repo, _snapshot("b"))
    repo.commit("second")

    # Reads the first commit's manifest without touching the checked-out tree.
    text = repo.read_file_at_ref(first.sha, "manifest.json")
    assert '"project_guid": "a"' in text
    current_guid = SnapshotCodec().read_manifest(repo.working_dir).project_guid
    assert current_guid == "b"  # the working tree itself was never switched


def test_read_file_at_ref_unknown_path_raises(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot())
    info = repo.commit("snap")

    with pytest.raises(RepositoryError):
        repo.read_file_at_ref(info.sha, "does/not/exist.jsonl")


def test_diff_reports_jsonl_changes_between_commits(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot("a"))
    first = repo.commit("first")
    _write_and_stage(repo, _snapshot("b"))
    repo.commit("second")

    summary = repo.diff(first.sha, "HEAD", stat=True)
    assert "element.jsonl" in summary
    assert repo.diff("HEAD", "HEAD") == ""


def test_merge_fast_forwards_a_branch(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    _write_and_stage(repo, _snapshot("base"))
    repo.commit("base")
    base = repo.current_branch()

    repo.create_branch("feature", checkout=True)
    _write_and_stage(repo, _snapshot("feature"))
    repo.commit("feature change")

    repo.checkout(base)
    repo.merge("feature", ff_only=True)
    guid = SnapshotCodec().read_manifest(repo.working_dir).project_guid
    assert guid == "feature"


def test_add_remote_is_idempotent_and_listed(tmp_path: Path) -> None:
    repo = init_repository(tmp_path)
    assert repo.remotes() == ()
    repo.add_remote("origin", str(tmp_path / "remote-a.git"))
    repo.add_remote("origin", str(tmp_path / "remote-b.git"))  # set-url, no dup
    assert repo.remotes() == ("origin",)


@pytest.mark.skipif(not is_lfs_available(), reason="git-lfs not installed")
def test_init_tracks_3d_and_3dc_with_lfs(tmp_path: Path) -> None:
    # A cadwork model may be saved as either .3d or .3dc, so both are tracked.
    init_repository(tmp_path)
    attributes = (tmp_path / ".gitattributes").read_text()
    assert "*.3d " in attributes or "*.3d\t" in attributes
    assert "*.3dc" in attributes
    assert "filter=lfs" in attributes

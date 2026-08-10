"""Contract tests for :class:`FakeRepository` — the no-git substitute.

The fake stands in for any :class:`~pycadwork.versioning.Repository`, so these
pin the behaviours the facade relies on: the commit graph advances, a checkout
swaps the on-disk tree, dirtiness is detected, and the LFS / remote hooks record
their inputs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.versioning._repository import Repository, RepositoryError
from tests._fakes.repository import FakeRepository


def _write(repo: FakeRepository, rel: str, text: str) -> Path:
    path = repo.working_dir / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_fake_satisfies_the_repository_protocol(fake_repo: FakeRepository) -> None:
    assert isinstance(fake_repo, Repository)


def test_starts_on_default_branch_clean_when_empty(fake_repo: FakeRepository) -> None:
    assert fake_repo.current_branch() == "main"
    assert fake_repo.branches() == ("main",)
    assert fake_repo.log() == ()


def test_untracked_file_makes_it_dirty(fake_repo: FakeRepository) -> None:
    assert not fake_repo.is_dirty()
    _write(fake_repo, "model/element.jsonl", "x")
    assert fake_repo.is_dirty()


def test_commit_records_and_clears_dirtiness(fake_repo: FakeRepository) -> None:
    path = _write(fake_repo, "model/element.jsonl", "x")
    fake_repo.stage([path])
    info = fake_repo.commit("first")

    assert info.message == "first"
    assert info.sha
    assert not fake_repo.is_dirty()
    assert [c.message for c in fake_repo.log()] == ["first"]


def test_log_is_newest_first(fake_repo: FakeRepository) -> None:
    _write(fake_repo, "a.txt", "1")
    fake_repo.commit("one")
    _write(fake_repo, "a.txt", "2")
    fake_repo.commit("two")
    assert [c.message for c in fake_repo.log()] == ["two", "one"]


def test_commit_metadata_is_deterministic(tmp_path: Path) -> None:
    def history() -> list[tuple[str, str]]:
        repo = FakeRepository(tmp_path / repo_name)
        (repo.working_dir / "a.txt").write_text("1")
        repo.commit("one")
        return [(c.sha, c.committed_at) for c in repo.log()]

    repo_name = "r1"
    first = history()
    repo_name = "r2"
    second = history()
    assert first == second


def test_branch_and_checkout_swap_the_tree(fake_repo: FakeRepository) -> None:
    target = fake_repo.working_dir / "model" / "element.jsonl"
    _write(fake_repo, "model/element.jsonl", "main-content")
    fake_repo.commit("on main")

    fake_repo.create_branch("feature", checkout=True)
    assert fake_repo.current_branch() == "feature"
    _write(fake_repo, "model/element.jsonl", "feature-content")
    fake_repo.commit("on feature")
    assert target.read_text() == "feature-content"

    fake_repo.checkout("main")
    assert fake_repo.current_branch() == "main"
    assert target.read_text() == "main-content"

    fake_repo.checkout("feature")
    assert target.read_text() == "feature-content"


def test_checkout_unknown_ref_raises(fake_repo: FakeRepository) -> None:
    with pytest.raises(RepositoryError):
        fake_repo.checkout("nope")


def test_status_reports_untracked_and_modified(fake_repo: FakeRepository) -> None:
    _write(fake_repo, "a.txt", "1")
    fake_repo.commit("one")
    _write(fake_repo, "a.txt", "2")  # modified
    _write(fake_repo, "b.txt", "new")  # untracked
    status = fake_repo.status()

    assert status.branch == "main"
    assert status.is_dirty
    assert status.modified == ("a.txt",)
    assert status.untracked == ("b.txt",)


def test_lfs_hooks_record_patterns(fake_repo: FakeRepository) -> None:
    fake_repo.ensure_lfs_tracked(("*.3dc",))
    fake_repo.ensure_lfs_tracked(("*.3dc",))  # idempotent
    assert fake_repo.lfs_tracked_patterns == ["*.3dc"]
    assert fake_repo.lfs_attribute_patterns == ["*.3dc"]


def test_remote_ops_are_recorded(fake_repo: FakeRepository) -> None:
    fake_repo.push("origin", "main")
    fake_repo.push("origin", "main", force=True)
    fake_repo.pull("origin", None)
    fake_repo.fetch("origin")
    assert fake_repo.push_calls == [("origin", "main", False), ("origin", "main", True)]
    assert fake_repo.pull_calls == [("origin", None)]
    assert fake_repo.fetch_calls == ["origin"]


def test_add_remote_is_idempotent_and_listed(fake_repo: FakeRepository) -> None:
    assert fake_repo.remotes() == ()
    fake_repo.add_remote("origin", "/srv/a.git")
    fake_repo.add_remote("origin", "/srv/b.git")  # updates, no duplicate
    assert fake_repo.remotes() == ("origin",)


def test_delete_branch_removes_it_but_not_the_current(
    fake_repo: FakeRepository,
) -> None:
    _write(fake_repo, "a.txt", "1")
    fake_repo.commit("base")
    fake_repo.create_branch("feature", checkout=False)
    assert "feature" in fake_repo.branches()

    fake_repo.delete_branch("feature")
    assert "feature" not in fake_repo.branches()

    with pytest.raises(RepositoryError):
        fake_repo.delete_branch(fake_repo.current_branch())


def test_merge_fast_forwards_and_swaps_tree(fake_repo: FakeRepository) -> None:
    target = fake_repo.working_dir / "a.txt"
    _write(fake_repo, "a.txt", "base")
    fake_repo.commit("base")
    main = fake_repo.current_branch()

    fake_repo.create_branch("feature", checkout=True)
    _write(fake_repo, "a.txt", "feature")
    fake_repo.commit("feature change")

    fake_repo.checkout(main)
    assert target.read_text() == "base"
    fake_repo.merge("feature", ff_only=True)
    assert target.read_text() == "feature"
    assert fake_repo.merge_calls == [("feature", True)]


def test_diff_reports_changed_files(fake_repo: FakeRepository) -> None:
    _write(fake_repo, "a.txt", "1")
    fake_repo.commit("base")
    base = fake_repo.current_branch()

    fake_repo.create_branch("feature", checkout=True)
    _write(fake_repo, "a.txt", "2")
    fake_repo.commit("change")

    diff = fake_repo.diff(base, "feature", stat=True)
    assert "a.txt" in diff
    assert fake_repo.diff(base, base) == ""

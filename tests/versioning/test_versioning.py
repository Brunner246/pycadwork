"""Fake-backed tests for the :class:`ModelVersioning` facade.

Driven by the autouse ``FakeCadworkAdapter`` (``tests/conftest.py``) for the
model side and a :class:`FakeRepository` for the git side, so the whole
commit → branch → checkout → restore loop runs with no cadwork process and no
git executable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.persistence import SnapshotDiff
from pycadwork.versioning import (
    CommitReport,
    ModelVersioning,
    RepositoryError,
    RestoreReport,
    is_git_available,
)
from pycadwork.versioning._codec import MODEL_DIR
from tests._fakes.repository import FakeRepository


@pytest.fixture
def saved_model(tmp_path: Path) -> Path:
    """Point the fake document at an absolute .3dc so the save seam materializes it."""
    path = tmp_path / "model.3dc"
    cadwork.project._state.model_file_name = str(path)
    return path


def _seed() -> tuple[Beam, Plate]:
    beam = Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 1)),
    )
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    return beam, plate


def _versioning(fake_repo: FakeRepository) -> ModelVersioning:
    return ModelVersioning.open(repo=fake_repo)


# ---- open ----


def test_open_with_repo_uses_it_verbatim(fake_repo: FakeRepository) -> None:
    vcs = ModelVersioning.open(repo=fake_repo)
    assert vcs.repository is fake_repo


def test_open_refuses_an_unsaved_model() -> None:
    cadwork.project._state.model_file_name = ""  # unsaved: no path to anchor on
    with pytest.raises(RepositoryError):
        ModelVersioning.open()


@pytest.mark.skipif(not is_git_available(), reason="git not available")
def test_open_accepts_a_non_3dc_saved_file(tmp_path: Path) -> None:
    # Versioning only needs a saved path — the extension does not have to be .3dc.
    cadwork.project._state.model_file_name = str(tmp_path / "model.3d")
    vcs = ModelVersioning.open()  # initializes a real repo in tmp_path
    assert vcs.repository.working_dir == tmp_path


# ---- commit ----


def test_commit_writes_tree_saves_binary_and_advances_log(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)

    report = vcs.commit("first snapshot")

    assert isinstance(report, CommitReport)
    assert not report.nothing_to_commit
    assert report.document_file == "model.3dc"
    assert report.files_changed > 0
    # JSONL tree + binary landed in the working tree
    assert (fake_repo.working_dir / MODEL_DIR / "element.jsonl").read_text().strip()
    assert (fake_repo.working_dir / "model.3dc").is_file()
    # the model was persisted through the save seam
    assert cadwork.project._state.save_count == 1
    # *.3dc was registered for LFS
    assert fake_repo.lfs_tracked_patterns == ["*.3dc"]
    assert [c.message for c in vcs.log()] == ["first snapshot"]


def test_second_identical_commit_is_nothing_to_commit(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("first")

    report = vcs.commit("second")

    assert report.nothing_to_commit
    assert report.files_changed == 0
    # no new commit was created
    assert [c.message for c in vcs.log()] == ["first"]


def test_commit_without_binary_skips_the_3dc(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)

    vcs.commit("jsonl only", include_binary=False)

    assert (fake_repo.working_dir / MODEL_DIR / "element.jsonl").read_text().strip()
    assert not (fake_repo.working_dir / "model.3dc").exists()
    assert fake_repo.lfs_tracked_patterns == []


# ---- model_status ----


def test_model_status_matches_committed_snapshot(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    beam, plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    status = vcs.model_status()

    assert isinstance(status, SnapshotDiff)
    # model and working-tree snapshot agree: both elements present in both
    assert set(status.dirty_ids) == {beam.id, plate.id}
    assert status.new_ids == ()
    assert status.removed == ()


# ---- restore ----


def test_restore_returns_the_binary_path_without_touching_model(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    report = vcs.restore()

    assert isinstance(report, RestoreReport)
    assert report.document_path == fake_repo.working_dir / "model.3dc"
    assert report.document_path.is_file()
    assert not report.applied_to_model
    assert (report.created, report.updated, report.deleted, report.skipped) == (
        0,
        0,
        0,
        0,
    )


def test_restore_apply_to_model_runs_write_back(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    report = vcs.load(apply_to_model=True)

    assert report.applied_to_model
    # both elements already exist in the model -> they count as updates
    assert report.updated >= 1
    assert report.created == 0


# ---- branch / checkout loop ----


def test_commit_branch_checkout_restore_loop(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("base")

    vcs.create_branch("feature", checkout=True)
    assert vcs.current_branch() == "feature"
    # add a third element and commit on the feature branch
    Beam.create_rectangular(
        RectSection(60, 120),
        AxisPoints(Point3D(1, 0, 0), Point3D(1, 1000, 0), Point3D(1, 0, 1)),
    )
    feature_report = vcs.commit("add beam")
    assert not feature_report.nothing_to_commit

    feature_lines = (
        (fake_repo.working_dir / MODEL_DIR / "element.jsonl").read_text().splitlines()
    )
    assert len(feature_lines) == 3

    vcs.checkout("main")
    base_lines = (
        (fake_repo.working_dir / MODEL_DIR / "element.jsonl").read_text().splitlines()
    )
    assert len(base_lines) == 2

    assert set(vcs.branches()) == {"main", "feature"}


# ---- git passthrough ----


def test_push_pull_delegate_to_the_repository(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    vcs.push("origin", "main")
    vcs.pull("origin")

    assert fake_repo.push_calls == [("origin", "main", False)]
    assert fake_repo.pull_calls == [("origin", None)]


def test_force_push_delegates_with_force(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    vcs.push("origin", "feature", force=True)

    assert fake_repo.push_calls == [("origin", "feature", True)]


def test_remote_helpers_delegate(fake_repo: FakeRepository, saved_model: Path) -> None:
    _seed()
    vcs = _versioning(fake_repo)

    assert vcs.remotes() == ()
    vcs.add_remote("origin", "/srv/repo.git")
    assert vcs.remotes() == ("origin",)


def test_branch_delete_merge_diff_round_trip(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("base")
    main = vcs.current_branch()

    vcs.create_branch("feature", checkout=True)
    Beam.create_rectangular(
        RectSection(60, 120),
        AxisPoints(Point3D(1, 0, 0), Point3D(1, 1000, 0), Point3D(1, 0, 1)),
    )
    vcs.commit("add beam on feature")

    # diff between base and feature shows the JSONL tree changed
    assert vcs.diff(main, "feature", stat=True)

    # merge the feature back into main, fast-forward only
    vcs.checkout(main)
    vcs.merge("feature", ff_only=True)
    assert (
        len(
            (fake_repo.working_dir / MODEL_DIR / "element.jsonl")
            .read_text()
            .splitlines()
        )
        == 3
    )

    # the feature branch can now be deleted (it is merged)
    vcs.delete_branch("feature")
    assert "feature" not in vcs.branches()

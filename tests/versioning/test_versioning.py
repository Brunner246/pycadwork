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
    Document,
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
    ReloadReport,
    RepositoryError,
    RestoreReport,
    SmartSwitchReport,
    SyncPlan,
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
    # JSONL tree + binary landed in the working tree (the binary under model/,
    # never at the root next to the cadwork-open live file)
    assert (fake_repo.working_dir / MODEL_DIR / "element.jsonl").read_text().strip()
    assert (fake_repo.working_dir / MODEL_DIR / "model.3dc").is_file()
    assert not (fake_repo.working_dir / "model.3dc").exists()
    # the live model file is kept out of git
    assert (
        (fake_repo.working_dir / ".gitignore")
        .read_text()
        .startswith("# Managed by pycadwork.versioning")
    )
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
    assert not (fake_repo.working_dir / MODEL_DIR / "model.3dc").exists()
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
    assert report.document_path == fake_repo.working_dir / MODEL_DIR / "model.3dc"
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


# ---- reload / switch: the version into the live model ----


def test_reload_model_smart_default_keeps_unchanged_elements_untouched(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    beam, plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    # A live edit since the commit: drop an element.
    Document().delete([beam])
    assert len(Document().elements()) == 1

    report = vcs.reload_model()

    assert isinstance(report, SmartSwitchReport)
    assert report.document_path == fake_repo.working_dir / MODEL_DIR / "model.3dc"
    # The unchanged plate is left alone; only the missing beam is brought back.
    assert report.unchanged == 1
    assert report.added == 1
    assert report.removed == 0
    assert report.total == 2
    assert len(Document().elements()) == 2
    assert plate.id in {e.id for e in Document().elements()}


def test_reload_model_full_strategy_matches_the_legacy_behaviour(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    beam, plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")

    Document().delete([beam])
    assert len(Document().elements()) == 1

    report = vcs.reload_model(strategy="full")

    assert isinstance(report, ReloadReport)
    assert report.imported == 2
    assert report.document_path == fake_repo.working_dir / MODEL_DIR / "model.3dc"
    assert len(Document().elements()) == 2
    # A full reimport reassigns ids to *every* element, even the untouched plate.
    assert plate.id not in {e.id for e in Document().elements()}


def test_reload_model_without_a_committed_binary_raises(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("jsonl only", include_binary=False)

    # No .3dc was committed, so there is nothing full-fidelity to reload.
    with pytest.raises(RepositoryError):
        vcs.reload_model()


def test_switch_to_restores_a_moved_element(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    """The regression guard: a moved element comes back, unchanged ones don't churn.

    The legacy ``restore(apply_to_model=True)`` write-back never moves existing
    elements, so this scenario silently failed before the binary reload. The
    smart-switch default additionally proves the other half of the feature:
    the untouched plate keeps its cadwork id/GUID across the switch, while only
    the actually-moved beam gets a fresh one.
    """
    beam, plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("base")
    main = vcs.current_branch()
    plate_guid = cadwork.attributes.get_cadwork_guid(plate.id)

    def positions() -> list[tuple[float, ...]]:
        return sorted(
            tuple(cadwork.geometry.get_p1(e.id)) for e in Document().elements()
        )

    base_positions = positions()

    vcs.create_branch("feature", checkout=True)
    # "Move" the beam. The adapter has no point setter by design, so a test
    # mutates the frame directly — exactly the edit the JSONL write-back could
    # not undo.
    cadwork.geometry._state.elements[beam.id].p1 = (9999.0, 1.0, 2.0)
    moved = vcs.commit("move the beam")
    assert not moved.nothing_to_commit
    assert positions() != base_positions  # the edit registered

    report = vcs.switch_to(main)

    assert isinstance(report, SmartSwitchReport)
    assert report.total == 2
    assert vcs.current_branch() == main
    assert positions() == base_positions  # the move was undone, full-fidelity
    # The unchanged plate kept its id/GUID; the moved beam's old id is gone.
    live_ids = {e.id for e in Document().elements()}
    assert plate.id in live_ids
    assert cadwork.attributes.get_cadwork_guid(plate.id) == plate_guid
    assert beam.id not in live_ids


def test_switch_to_full_strategy_reassigns_every_id(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _beam, plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("base")
    main = vcs.current_branch()

    vcs.create_branch("feature", checkout=True)
    cadwork.geometry._state.elements[_beam.id].p1 = (9999.0, 1.0, 2.0)
    vcs.commit("move the beam")

    report = vcs.switch_to(main, strategy="full")

    assert isinstance(report, ReloadReport)
    assert report.imported == 2
    assert plate.id not in {e.id for e in Document().elements()}


def test_switch_smart_skips_import_when_nothing_is_missing(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    """A pure-removal switch never touches the binary — the actual "smart" payoff."""
    beam, plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("base")
    main = vcs.current_branch()

    vcs.create_branch("feature", checkout=True)
    Beam.create_rectangular(
        RectSection(60, 120),
        AxisPoints(Point3D(5, 0, 0), Point3D(5, 1000, 0), Point3D(5, 0, 1)),
    )
    vcs.commit("add a beam")

    imports_before = cadwork.file._state.import_calls
    report = vcs.switch_to(main)

    assert isinstance(report, SmartSwitchReport)
    assert report.unchanged == 2
    assert report.added == 0
    assert report.removed == 1
    assert report.total == 2
    assert cadwork.file._state.import_calls == imports_before
    assert {e.id for e in Document().elements()} == {beam.id, plate.id}


# ---- sync preview: no git, no checkout ----


def test_sync_status_previews_without_touching_the_model(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    beam, _plate = _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("snap")
    Document().delete([beam])

    plan = vcs.sync_status()

    assert isinstance(plan, SyncPlan)
    assert plan.stale == ()
    assert len(plan.missing) == 1
    assert len(Document().elements()) == 1  # preview only, model untouched


def test_preview_switch_reads_the_target_ref_without_checking_it_out(
    fake_repo: FakeRepository, saved_model: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    vcs.commit("base")
    main = vcs.current_branch()

    vcs.create_branch("feature", checkout=True)
    Beam.create_rectangular(
        RectSection(60, 120),
        AxisPoints(Point3D(5, 0, 0), Point3D(5, 1000, 0), Point3D(5, 0, 1)),
    )
    vcs.commit("add a beam")

    plan = vcs.preview_switch(main)

    assert isinstance(plan, SyncPlan)
    assert len(plan.unchanged) == 2
    assert len(plan.stale) == 1
    assert plan.missing == ()
    assert vcs.current_branch() == "feature"  # pure preview, nothing switched


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


def test_ensure_local_remote_inits_a_bare_repo_and_wires_it(
    fake_repo: FakeRepository, saved_model: Path, tmp_path: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)
    backup = tmp_path / "backup.git"

    name = vcs.ensure_local_remote(backup, name="backup")

    assert name == "backup"
    assert vcs.remotes() == ("backup",)
    # The bare remote was initialized (no network) and the remote points at it.
    assert fake_repo.local_remote_paths == [str(backup)]
    assert fake_repo._remotes["backup"] == str(backup)


def test_ensure_local_remote_defaults_to_origin(
    fake_repo: FakeRepository, saved_model: Path, tmp_path: Path
) -> None:
    _seed()
    vcs = _versioning(fake_repo)

    assert vcs.ensure_local_remote(tmp_path / "origin.git") == "origin"
    assert vcs.remotes() == ("origin",)


# ---- real-git: the repo hosted in the model's own directory ----


@pytest.mark.skipif(
    not is_git_available(), reason="git executable / GitPython not available"
)
def test_real_repo_in_model_dir_keeps_open_file_out_of_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduce the cadwork layout (repo root == the model's own folder).

    The live ``.3dc`` cadwork would hold open must stay *out* of git, and the
    versioned copy must live under ``model/``, so a branch ``checkout`` only ever
    rewrites files under ``model/`` — never the open file. Before the fix the
    binary was tracked at the root and a checkout had to overwrite it, which
    Windows refuses while cadwork has it open.
    """
    for key, value in {
        "GIT_AUTHOR_NAME": "Test Bot",
        "GIT_AUTHOR_EMAIL": "bot@example.com",
        "GIT_COMMITTER_NAME": "Test Bot",
        "GIT_COMMITTER_EMAIL": "bot@example.com",
    }.items():
        monkeypatch.setenv(key, value)

    live_file = tmp_path / "model.3dc"
    cadwork.project._state.model_file_name = str(live_file)
    _seed()
    vcs = ModelVersioning.open(root=tmp_path, init=True)

    base = vcs.commit("base")
    assert not base.nothing_to_commit
    # The versioned binary copy is under model/, never at the root next to the
    # live file; the live file exists on disk but git ignores it (clean status).
    assert (tmp_path / MODEL_DIR / "model.3dc").is_file()
    assert live_file.is_file()
    status = vcs.status()
    assert not status.is_dirty
    assert status.untracked == ()

    # Branch, change the model, commit — then switch back. The checkout must
    # succeed without ever needing to touch the (would-be open) root file.
    main = vcs.current_branch()
    vcs.create_branch("feature")
    Beam.create_rectangular(
        RectSection(60, 120),
        AxisPoints(Point3D(500, 0, 0), Point3D(500, 3000, 0), Point3D(500, 0, 1)),
    )
    vcs.commit("add a beam on feature")
    vcs.checkout(main)

    assert vcs.current_branch() == main
    assert not vcs.status().is_dirty


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

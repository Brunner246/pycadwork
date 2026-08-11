"""A git workflow over a cadwork model — commit, branch, model-aware checkout.

``pycadwork.versioning`` turns the live model into a git history you can review.
A :meth:`ModelVersioning.commit` captures the model as *both* a deterministic,
line-diffable JSONL tree (the reviewable artifact) and the binary ``.3dc`` (the
full-fidelity artifact). By default ``checkout`` / ``pull`` / ``merge`` update
git **and** load the resulting version into the live model. Pass
``apply_to_model=False`` for pure working-tree operations.

    uv run python -m examples.versioning

These demos run against a :class:`FakeRepository` inside a throwaway temp
directory, so they execute in CI **with no git executable** — the only footprint
is that temp dir. Real use is identical but with a real repository::

    from pycadwork.versioning import ModelVersioning

    vcs = ModelVersioning.open()        # repo in the active .3dc's directory
    vcs.commit("framed the north wall")
    vcs.checkout("main")                # git + load main into the live model

.. note::

   Seeding the model and pointing the document at a temp ``.3dc`` below go
   through the version-isolation seam (``pycadwork.cadwork_adapter.cadwork``).
   That is *setup that mimics the cadwork UI* (modeling, then File ▸ Save) — not
   part of normal pycadwork usage. In real cadwork the model and its saved
   ``.3dc`` path already exist.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from pycadwork import (
    AxisPoints,
    Beam,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
)

# Seam access — only for the UI-mimicking setup (pointing at a saved .3dc).
from pycadwork.cadwork_adapter import cadwork
from pycadwork.versioning import ModelVersioning, is_git_available
from tests._fakes.repository import FakeRepository


def _seed_model() -> None:
    """A small model to version: one beam, one plate (mimics modeling)."""
    Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 1)),
    )
    Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


def _point_document_at(directory: Path) -> None:
    """Point the active document at ``directory/model.3dc`` (mimics File ▸ Save).

    Real cadwork already knows the saved path; here we set it on the fake so the
    save seam materializes a placeholder ``.3dc`` the commit can track. Skipped
    automatically outside the fake.
    """
    project = cadwork.project
    if hasattr(project, "_state"):
        project._state.model_file_name = str(directory / "model.3dc")


def demo_commit_and_log(vcs: ModelVersioning) -> None:
    """`commit` captures the model (JSONL + .3dc) into one git commit."""
    report = vcs.commit("initial model")
    print(
        f"commit: files_changed={report.files_changed} "
        f"document_file={report.document_file!r} sha={report.commit.sha[:8]}"
    )

    # A second commit with no changes is a safe no-op.
    again = vcs.commit("no changes")
    print(f"re-commit: nothing_to_commit={again.nothing_to_commit}")

    print("log =", [c.message for c in vcs.log()])


def demo_branch_and_checkout(vcs: ModelVersioning) -> None:
    """Branch, change the model, commit — then model-aware checkout loads ``main``."""
    vcs.create_branch("add-purlin", checkout=True)
    print("branch ->", vcs.current_branch())

    Beam.create_rectangular(  # mimics adding an element on the branch
        RectSection(60, 120),
        AxisPoints(Point3D(500, 0, 0), Point3D(500, 3000, 0), Point3D(500, 0, 1)),
    )
    vcs.commit("add a purlin")

    # Default checkout is model-aware: git switch + load main into the live model.
    # Pure git only: vcs.checkout("main", apply_to_model=False)
    report = vcs.checkout("main")
    print(
        "branches =",
        vcs.branches(),
        "now on",
        vcs.current_branch(),
        f"(reload: {_report_line(report)})",
    )


def demo_diff_and_merge(vcs: ModelVersioning) -> None:
    """`diff` reviews the JSONL change; `merge` folds a branch back — all via the facade.

    No ``subprocess`` / raw ``git`` anywhere: the facade wraps diff and merge too.
    Merge is model-aware by default (loads the merged version after success).
    """
    # We are on main; `add-purlin` has one extra commit. Diff is the reviewable
    # payoff of committing a deterministic JSONL tree alongside the binary.
    summary = vcs.diff("main", "add-purlin", stat=True)
    print("diff main..add-purlin:", summary.replace("\n", " | ") or "(no changes)")

    report = vcs.merge("add-purlin", ff_only=True)  # fast-forward + load
    print(
        "after merge, on",
        vcs.current_branch(),
        "log =",
        [c.message for c in vcs.log()],
        f"(reload: {_report_line(report)})",
    )


def demo_model_status(vcs: ModelVersioning) -> None:
    """`model_status` previews how the live model differs from the working tree.

    After a model-aware checkout of ``main``, live model and working tree match
    for the committed elements (no uncommitted delta left from the branch).
    """
    status = vcs.model_status()
    print(
        f"model vs working tree: new={list(status.new_ids)} "
        f"common={list(status.dirty_ids)} removed={[r.id for r in status.removed]}"
    )


def demo_pure_git_escape(vcs: ModelVersioning) -> None:
    """``apply_to_model=False`` keeps pure working-tree checkout available."""
    pure = vcs.checkout("add-purlin", apply_to_model=False)
    print(
        f"pure-git checkout add-purlin: report={pure!r}, "
        f"branch={vcs.current_branch()!r}"
    )
    # Return to main with the default model-aware path for later demos.
    vcs.checkout("main", force=True)


def demo_restore(vcs: ModelVersioning) -> None:
    """`restore` returns the working-tree ``.3dc`` path (e.g. to reopen by hand)."""
    report = vcs.restore()
    print(
        f"restore: reopen {report.document_path.name} "
        f"(exists={report.document_path.is_file()}), "
        f"applied_to_model={report.applied_to_model}"
    )


def _report_line(report: object | None) -> str:
    """One-line summary for a reload/smart-switch report (or pure-git ``None``)."""
    if report is None:
        return "none (apply_to_model=False)"
    if hasattr(report, "added"):
        return (
            f"unchanged={report.unchanged} added={report.added} "
            f"removed={report.removed} total={report.total}"
        )
    if hasattr(report, "imported"):
        return f"imported={report.imported}"
    return repr(report)


def demo_real_repo_note() -> None:
    """How the same workflow runs against a real git repository."""
    available = is_git_available()
    print(f"git available here: {available}")
    print(
        "real use: `ModelVersioning.open()` initializes/opens a real git repo in "
        "the active .3dc's directory (LFS-tracking *.3dc); the demos above are "
        "identical but backed by a FakeRepository so they run without git."
    )


def run() -> None:
    """Run every versioning demo against a FakeRepository in a temp directory."""
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        _seed_model()
        _point_document_at(directory)

        repo = FakeRepository(directory / "repo")
        vcs = ModelVersioning.open(repo=repo)

        demo_commit_and_log(vcs)
        demo_branch_and_checkout(vcs)
        demo_model_status(vcs)
        demo_pure_git_escape(vcs)
        demo_restore(vcs)
        demo_diff_and_merge(vcs)
    demo_real_repo_note()


if __name__ == "__main__":
    run()

"""Run a real git *workflow* over the live cadwork model — execute inside cadwork.

This is the real-environment companion to :mod:`examples.versioning` (which runs
against a fake repository so CI can exercise it). This one talks to the **live
model** and a **real git repository**, so it only does anything useful inside a
running cadwork process with a saved model — it is deliberately *not* part of the
CI example tour (not listed in ``examples.MODULES``).

How to run it inside cadwork:

1. Provision pycadwork into cadwork's embedded interpreter once — from the
   pycadwork checkout run ``scripts\\Install-PycadworkRuntime.ps1`` (see the
   README, "Using pycadwork inside cadwork"). Add the git backend with
   ``pip install 'pycadwork[git]'`` into that same interpreter, and make sure a
   ``git`` executable (ideally with ``git-lfs``) is on PATH.
2. Copy this file into your cadwork userprofile API folder, e.g.
   ``<userprofile>\\<version>\\API.x64\\pycadwork_versioning\\main.py``.
3. **Save your model** (File ▸ Save) so it has a file on disk, then run the
   script from cadwork's API menu.

What it does — a full branch / edit / diff / merge round-trip:

1. Commits the current model as a baseline on the active branch.
2. Branches off, **creates a real beam in the live model**, and commits it.
3. Shows the change two ways: :meth:`~ModelVersioning.model_status` (the
   *id-level* delta vs HEAD — which elements were added/deleted, by id) and a
   textual ``git diff`` of the JSONL tree (the *field-level* changes — a moved
   point, a renamed attribute — that an id-keyed diff can't see).
4. Switches back to the original branch and **fast-forward merges** the branch.

⚠️ **It mutates your model**: step 2 adds a beam named ``versioning-demo-beam``
(re-runs reuse the existing one instead of piling up). Delete it when you're done.

Two notes on the design this example leans on:

* ``merge`` and textual ``diff`` go through the :class:`ModelVersioning` facade
  (:meth:`~ModelVersioning.merge` / :meth:`~ModelVersioning.diff`) — you never
  shell out to ``git`` yourself. Direction is always your explicit choice (no
  auto-merge), and the binary model file can't be line-merged: a conflicting
  merge raises :class:`MergeConflictError`, which you resolve in git and reopen.
* ``checkout`` switches the *git files* only — it never rewinds the *live model*.
  Bringing a committed version back into cadwork is the separate, explicit
  :meth:`~ModelVersioning.restore` step (it returns the model file to reopen).
"""

from __future__ import annotations

try:
    import pycadwork  # noqa: F401  (import-only check the runtime install is in place)
    from pycadwork import AxisPoints, Beam, Document, Point3D, RectSection
    from pycadwork.versioning import (
        ModelVersioning,
        RepositoryError,
        is_git_available,
        is_lfs_available,
    )
except (
    ImportError
) as exc:  # pragma: no cover - guidance for an un-provisioned interpreter
    raise ImportError(
        "pycadwork is not importable from cadwork's interpreter. From the "
        "pycadwork checkout, run scripts\\Install-PycadworkRuntime.ps1 to link the "
        "package and install its dependencies into cadwork's site-packages, then "
        "install the git backend with: pip install 'pycadwork[git]'."
    ) from exc

DEMO_BRANCH = "pycadwork/versioning-demo"
DEMO_BEAM_NAME = "versioning-demo-beam"


def _preflight() -> bool:
    """Check the environment is ready; print clear guidance and return False if not.

    Versioning only needs the model **saved to disk** — any 3d file works, the
    extension does not have to be ``.3dc``.
    """
    if not Document().file_path:
        print(
            "The model is unsaved. Save the 3d file (File ▸ Save) so it has a "
            "path on disk, then run this again."
        )
        return False
    if not is_git_available():
        print(
            "git is not available. Install the backend into cadwork's interpreter "
            "(pip install 'pycadwork[git]') and put a `git` executable on PATH."
        )
        return False
    if not is_lfs_available():
        print(
            "warning: git-lfs is not installed — the model file will be committed "
            "as an ordinary (large) git blob. Install git-lfs for efficient "
            "versioning."
        )
    return True


def commit_baseline(vcs: ModelVersioning, message: str) -> str:
    """Commit the current model so the branch has a parent; return the baseline sha."""
    report = vcs.commit(message)
    if report.nothing_to_commit:
        print(f"baseline: already committed at {report.commit.sha[:8]}")
    else:
        print(f"baseline: committed {report.commit.sha[:8]} ({message})")
    return report.commit.sha


def switch_to_demo_branch(vcs: ModelVersioning) -> None:
    """Create the demo branch (or check it out if a previous run made it)."""
    if DEMO_BRANCH in vcs.branches():
        vcs.checkout(DEMO_BRANCH)
        print(f"branch:   checked out existing {DEMO_BRANCH!r}")
    else:
        vcs.create_branch(DEMO_BRANCH)  # checkout=True by default
        print(f"branch:   created and checked out {DEMO_BRANCH!r}")


def add_demo_beam() -> Beam | None:
    """Add a recognizable beam to the live model (idempotent across re-runs)."""
    existing = [
        b for b in Document().elements_of(Beam) if b.attrs.name == DEMO_BEAM_NAME
    ]
    if existing:
        print(f"element:  {DEMO_BEAM_NAME!r} already present — skipping creation")
        return existing[0]

    beam = Beam.create_rectangular(
        RectSection(width=120.0, height=240.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    beam.attrs.name = DEMO_BEAM_NAME
    beam.attrs.group = "versioning-demo"
    print(f"element:  created {DEMO_BEAM_NAME!r} (id {beam.id})")
    return beam


def show_model_diff(vcs: ModelVersioning) -> None:
    """Print the id-level delta between the live model and the last commit.

    ``model_status()`` is ``diff(live model, last commit)`` — a preview of what
    :meth:`~ModelVersioning.restore` would do to return the model to HEAD. It
    classifies elements **by id only**, so its fields read in that restore
    direction:

    * ``removed`` — ids in the live model but not in the commit → your
      **uncommitted additions** (the demo beam lands here before you commit it).
    * ``new_ids`` — ids in the commit but not in the live model → elements
      **deleted** from the model since HEAD.
    * ``dirty_ids`` — ids present in **both** (the intersection; *not* a
      content comparison — it does not mean "edited").

    Because it is id-keyed, ``model_status`` cannot see a field-level edit (a
    moved point, a renamed attribute) on an element that still exists — those
    show up only in the textual ``git diff`` of the JSONL (see below).
    """
    preview = vcs.model_status()  # pure diff vs HEAD, no git
    added = [r.id for r in preview.removed]  # in model, not in commit → added
    print(
        f"model vs HEAD: uncommitted-additions={added} "
        f"deleted-since-HEAD={len(preview.new_ids)} unchanged-set={len(preview.dirty_ids)}"
    )
    status = vcs.status()  # git working-tree status
    print(
        f"git status:    dirty={status.is_dirty} "
        f"untracked={len(status.untracked)} modified={len(status.modified)}"
    )


def show_text_diff(vcs: ModelVersioning, baseline_sha: str) -> None:
    """Show the reviewable, line-level ``git diff`` of the JSONL between two commits.

    This is the payoff of committing a deterministic JSONL tree alongside the
    binary: ``vcs.diff`` is meaningful, where a diff of the raw model file is not.
    """
    diff_stat = vcs.diff(baseline_sha, "HEAD", stat=True)
    print("diff (baseline..HEAD):")
    print("  " + (diff_stat.strip().replace("\n", "\n  ") or "(no textual changes)"))
    print("  (call vcs.diff(baseline_sha, 'HEAD') for the full per-line JSONL diff)")


def merge_back(vcs: ModelVersioning, target_branch: str) -> None:
    """Fast-forward merge the demo branch into ``target_branch`` through the facade."""
    vcs.checkout(target_branch)
    print(f"merge:    checked out {target_branch!r}")
    vcs.merge(DEMO_BRANCH, ff_only=True)
    print(f"  fast-forwarded {target_branch!r} to {DEMO_BRANCH!r}")

    restored = vcs.restore()  # the merged model file you'd reopen in cadwork
    print(f"restore:  reopen {restored.document_path} to load the merged version")
    print(
        "  (the live model already holds the demo beam — restore matters when you "
        "pick this version up on another machine)"
    )


def run_workflow() -> None:
    """The full round-trip: baseline → branch + edit → diff → merge."""
    vcs = ModelVersioning.open()  # repo in the model's directory (init on first run)
    original_branch = vcs.current_branch()
    print(f"repository: {vcs.repository.working_dir}")
    print(f"branch:     {original_branch}")

    baseline_sha = commit_baseline(vcs, "snapshot from cadwork")

    switch_to_demo_branch(vcs)
    add_demo_beam()
    show_model_diff(
        vcs
    )  # beam now in the model but not HEAD -> uncommitted-additions=[id]

    report = vcs.commit("add the demo beam")
    if report.nothing_to_commit:
        print("commit:   nothing to commit — branch already matches the model")
    else:
        print(f"commit:   {report.commit.sha[:8]} ({report.files_changed} files)")
    show_model_diff(vcs)  # now in sync

    show_text_diff(vcs, baseline_sha)
    merge_back(vcs, original_branch)

    print("recent history:")
    for entry in vcs.log(max_count=5):
        print(f"  {entry.sha[:8]}  {entry.committed_at}  {entry.message}")


def main() -> None:
    """Entry point — preflight, then run the branch / edit / diff / merge workflow."""
    if not _preflight():
        return
    try:
        run_workflow()
    except RepositoryError as exc:
        print(f"versioning failed: {exc}")


if __name__ == "__main__":
    main()

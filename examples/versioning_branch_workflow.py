"""Branch / push / switch-back lifecycle over the live model — run inside cadwork.

A second real-environment companion to :mod:`examples.versioning` (the CI-safe,
fake-repository tour). Like :mod:`examples.versioning_in_cadwork` it talks to the
**live model** and a **real git repository**, so it only does useful work inside a
running cadwork process with a saved model — it is deliberately *not* part of the
CI example tour (not listed in ``examples.MODULES``).

It walks the exact lifecycle you'd reach for to try an idea on a branch without
touching ``main``:

1. Initialize the repo and commit the current model as a baseline on ``main``.
2. Branch off, **create 5 beams in the live model**, commit, and **push** the
   branch to a remote.
3. Switch back to ``main`` — **without merging** — and get the model back to the
   baseline (the 5 beams gone from the running model).

⚠️ **The one thing that surprises everyone** — ``checkout`` switches the *git
files* only; it does **not** rewind the *live cadwork model*. So right after
``checkout('main')`` the 5 beams are *still* in your model. They disappear only
when you **apply** ``main``'s snapshot back to the model with
``restore(apply_to_model=True)`` — which deletes the elements that ``main`` does
not have. This example prints the model's beam count at each step so you can see
exactly when they go.

⚠️ **It mutates your model**: it adds 5 beams in the group ``five-beams-workflow``
and then deletes them again on the way back to ``main``. They live on safely on
the ``feature/five-beams`` branch (locally and on the remote); ``main`` is never
merged, so re-applying the branch later brings them back.

How to run it inside cadwork: see the header of
:mod:`examples.versioning_in_cadwork` — provision pycadwork into cadwork's
interpreter, install the git backend (``pip install 'pycadwork[git]'``), put a
``git`` executable on PATH, save your model, then run this from the API menu.
"""

from __future__ import annotations

try:
    import pycadwork  # noqa: F401  (import-only check the runtime install is in place)
    from pycadwork import AxisPoints, Beam, Document, Point3D, RectSection
    from pycadwork.versioning import (
        ModelVersioning,
        RepositoryError,
        init_bare_repository,
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

BRANCH = "feature/five-beams"
DEMO_GROUP = "five-beams-workflow"
BEAM_COUNT = 5


def _preflight() -> bool:
    """Check the environment is ready; print clear guidance and return False if not."""
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


def count_demo_beams() -> int:
    """How many of this example's beams currently exist in the *live* model."""
    return sum(1 for b in Document().elements_of(Beam) if b.attrs.group == DEMO_GROUP)


def ensure_demo_remote(vcs: ModelVersioning) -> str:
    """Return the ``origin`` remote, wiring a throwaway local one if none exists.

    In real use you'd call ``vcs.add_remote('origin', '<your-server-url>')`` once
    and push there; here we point ``origin`` at a sibling **bare** repo (created
    with :func:`init_bare_repository`) so the example's ``push`` is self-contained
    (no network, no credentials). Everything goes through the facade — no raw git.
    """
    if "origin" in vcs.remotes():
        return "origin"
    working = vcs.repository.working_dir
    bare = working.parent / f"{working.name}-demo-remote.git"
    init_bare_repository(bare)
    vcs.add_remote("origin", str(bare))
    print(f"remote:   wired throwaway local origin -> {bare}")
    print("          (real use: vcs.add_remote('origin', '<your-server-url>'))")
    return "origin"


def recreate_branch(vcs: ModelVersioning, name: str, base_branch: str) -> None:
    """Create ``name`` fresh off ``base_branch`` (resetting it if a re-run left one)."""
    vcs.checkout(base_branch)
    if name in vcs.branches():
        vcs.delete_branch(name, force=True)
        print(f"branch:   reset existing {name!r}")
    vcs.create_branch(name)  # checkout=True
    print(f"branch:   created {name!r} off {base_branch!r}")


def add_beams(count: int) -> None:
    """Create ``count`` beams in the live model, tagged with the demo group."""
    for i in range(count):
        y = i * 300.0
        beam = Beam.create_rectangular(
            RectSection(width=120.0, height=240.0),
            AxisPoints(Point3D(0, y, 0), Point3D(2400, y, 0), Point3D(0, 0, 1)),
        )
        beam.attrs.group = DEMO_GROUP
        beam.attrs.name = f"{DEMO_GROUP}-{i + 1}"


def push_branch(vcs: ModelVersioning, remote: str, name: str) -> None:
    """Push ``name`` to ``remote`` via the facade; force on a re-run divergence."""
    try:
        vcs.push(remote, name)
        print(f"push:     pushed {name!r} -> {remote!r}")
    except RepositoryError:
        # A previous run left a diverged branch on the demo remote — safe to force
        # here because origin is the throwaway local repo this example created.
        vcs.push(remote, name, force=True)
        print(f"push:     force-pushed {name!r} -> {remote!r} (re-run)")


def run_workflow() -> None:
    """Init → baseline on main → branch + 5 beams + push → back to main (beams gone)."""
    vcs = ModelVersioning.open()  # inits the repo in the model's dir on first run
    main_branch = vcs.current_branch()
    print(f"repository: {vcs.repository.working_dir}")
    print(f"branch:     {main_branch}")

    base = vcs.commit("snapshot from cadwork")
    print(
        f"baseline:  {'already at' if base.nothing_to_commit else 'committed'} "
        f"{base.commit.sha[:8]} on {main_branch!r} "
        f"(demo beams in model: {count_demo_beams()})"
    )
    remote = ensure_demo_remote(vcs)

    # --- work on a branch ---
    recreate_branch(vcs, BRANCH, main_branch)
    add_beams(BEAM_COUNT)
    print(f"element:   created {BEAM_COUNT} beams (model now has {count_demo_beams()})")

    report = vcs.commit(f"add {BEAM_COUNT} beams")
    print(
        f"commit:    {report.commit.sha[:8]} ({report.files_changed} files) on {BRANCH!r}"
    )
    push_branch(vcs, remote, BRANCH)

    # --- switch back to main WITHOUT merging ---
    vcs.checkout(main_branch)
    print(f"\ncheckout {main_branch!r}:")
    print(
        f"  git files now match {main_branch!r}, but the LIVE MODEL still has "
        f"{count_demo_beams()} demo beams —"
    )
    print("  checkout switches git files only; it never touches the running model.")

    # Apply main's snapshot back to the model: elements main lacks get deleted.
    result = vcs.restore(apply_to_model=True)
    print(
        f"restore(apply_to_model=True): created={result.created} "
        f"updated={result.updated} deleted={result.deleted} skipped={result.skipped}"
    )
    print(f"  live model now has {count_demo_beams()} demo beams — gone, as expected.")

    print(
        f"\nthe {BEAM_COUNT} beams are safe on {BRANCH!r} (local + {remote!r}); "
        f"{main_branch!r} was never merged.\n"
        f"to bring them back: vcs.checkout({BRANCH!r}); "
        "vcs.restore(apply_to_model=True)."
    )


def main() -> None:
    """Entry point — preflight, then run the branch / push / switch-back workflow."""
    if not _preflight():
        return
    try:
        run_workflow()
    except RepositoryError as exc:
        print(f"versioning failed: {exc}")


if __name__ == "__main__":
    main()

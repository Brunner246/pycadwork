# This is the SEQUENTIAL, no-functions version of examples/versioning_branch_workflow.py,
# meant to be pasted into cadwork's interactive Python shell ONE LINE AT A TIME so
# you can watch each step. It walks the same lifecycle:
#
#   commit baseline on main -> branch -> add 5 beams -> commit -> push
#   -> switch back to main (the beams are STILL in the live model!)
#   -> restore(apply_to_model=True)  (now the beams are gone)
#
# THE GOTCHA this demonstrates: vcs.checkout("main") switches the *git files* only.
# It does NOT rewind the *live cadwork model* — your 5 beams are still there after
# the checkout. They disappear only when you apply main's snapshot back into the
# model with restore(apply_to_model=True), which deletes elements main doesn't have.
#
# Prerequisites (see examples/versioning_in_cadwork.py for the full setup):
#   * pycadwork provisioned into cadwork's interpreter + `pip install 'pycadwork[git]'`
#   * a `git` executable (ideally with git-lfs) on PATH
#   * your model SAVED to disk (File > Save)
#
# It mutates your model: adds 5 beams in group "five-beams-workflow", then deletes
# them on the way back to main. They stay safe on the branch; main is never merged.

# --- imports ---
from pycadwork import AxisPoints, Beam, Document, Point3D, RectSection
from pycadwork.versioning import ModelVersioning, init_bare_repository

GROUP = "five-beams-workflow"
BRANCH = "feature/five-beams"

# --- open the repo (initializes one in the model's directory on first run) ---
vcs = ModelVersioning.open()
working = str(vcs.repository.working_dir)
main_branch = vcs.current_branch()
print("repo:", working, "| branch:", main_branch)

# --- commit the current model as a baseline on main ---
base = vcs.commit("snapshot from cadwork")
print("baseline:", base.commit.sha[:8], "nothing_to_commit:", base.nothing_to_commit)

# --- (optional) wire a throwaway LOCAL remote called "demo" so push works offline ---
# In real use you already have an origin: skip these 2 lines and push to "origin".
bare = working + "-demo-remote.git"
init_bare_repository(bare)
vcs.add_remote("demo", bare)  # idempotent — updates the URL if "demo" already exists

# --- create the branch off main (delete a leftover one from an earlier run first) ---
vcs.checkout(main_branch)
if BRANCH in vcs.branches():
    vcs.delete_branch(BRANCH, force=True)
vcs.create_branch(BRANCH)
print("on branch:", vcs.current_branch())

# --- add 5 beams to the LIVE model (one-line comprehension) and tag them ---
beams = [
    Beam.create_rectangular(
        RectSection(width=120.0, height=240.0),
        AxisPoints(
            Point3D(0, i * 300.0, 0), Point3D(2400, i * 300.0, 0), Point3D(0, 0, 1)
        ),
    )
    for i in range(5)
]
for i, b in enumerate(beams):
    b.attrs.group = GROUP
    b.attrs.name = GROUP + "-" + str(i + 1)
print(
    "demo beams in model:",
    sum(1 for b in Document().elements_of(Beam) if b.attrs.group == GROUP),
)  # -> 5

# --- commit the 5 beams on the branch and push ---
report = vcs.commit("add 5 beams")
print("commit:", report.commit.sha[:8], "files:", report.files_changed)
# force=True overwrites a branch left on the demo remote by an earlier run (safe
# here — "demo" is the throwaway local repo created above).
vcs.push("demo", BRANCH, force=True)
print("pushed", BRANCH, "to demo")

# --- switch back to main WITHOUT merging ---
vcs.checkout(main_branch)
print("checked out:", vcs.current_branch())
print(
    "demo beams in model AFTER checkout:",
    sum(1 for b in Document().elements_of(Beam) if b.attrs.group == GROUP),
)  # -> still 5 (checkout = git files only!)

# --- apply main's snapshot back into the model: the 5 beams (absent on main) get deleted ---
result = vcs.restore(apply_to_model=True)
print(
    "restore: created",
    result.created,
    "updated",
    result.updated,
    "deleted",
    result.deleted,
    "skipped",
    result.skipped,
)
print(
    "demo beams in model AFTER restore:",
    sum(1 for b in Document().elements_of(Beam) if b.attrs.group == GROUP),
)  # -> 0, gone

# The 5 beams are safe on the branch (local + demo remote); main was never merged.
# To bring them back later:
#   vcs.checkout(BRANCH)
#   vcs.restore(apply_to_model=True)

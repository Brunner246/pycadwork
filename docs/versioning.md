# Versioning: a git workflow over the model

A cadwork model is a binary `.3dc` — git can store it but cannot *diff* it.
`pycadwork.versioning` adds a real git workflow (commit / branch / checkout /
push / pull) **plus** a machine-readable serialization so changes are reviewable.
It is a thin bridge between three existing pieces:

```text
model  ⇄  ModelSnapshot     (reuses pycadwork.persistence)
       ⇄  diffable JSONL     (SnapshotCodec — deterministic, PK-sorted, one object/line)
       ⇄  git                (Repository seam; GitRepository over GitPython, lazy-loaded)
```

A `commit` **losslessly** captures the model as *both* a per-table JSONL tree
(the reviewable, line-diffable artifact) and the saved `.3dc` tracked via **Git
LFS** (the full-fidelity artifact a checkout restores for reopening in cadwork).

```python
from pycadwork.versioning import ModelVersioning

vcs = ModelVersioning.open()                 # repo in the active .3dc's directory
report = vcs.commit("framed the north wall") # saves .3dc + writes JSONL + commits
print(report.commit.sha, report.files_changed, report.document_file)

vcs.create_branch("alternative-roof")        # ordinary git branching
...
vcs.checkout("main")                         # switches git files only
restored = vcs.restore()                     # restored.document_path -> reopen in cadwork
```

`restore()` (alias `load()`) always returns the working-tree `.3dc` path to
reopen — the **full-fidelity, primary** restore. `restore(apply_to_model=True)`
*additionally* runs a **best-effort** JSON write-back through the persistence
`ModelWriter`; per its limits, existing elements' points are never moved and
non-reconstructable types are skipped (counted in `RestoreReport.skipped`). The
binary is therefore the guarantee; the JSONL is the review aid. `model_status()`
is a pure preview — `diff(live model, working-tree snapshot)` — needing no git.

## Honest limitations

Stated in the docstrings too:

- **GitPython is an optional extra** (`pip install 'pycadwork[git]'`) and a `git`
  executable is required at runtime — both are often absent inside cadwork.
  `import pycadwork.versioning` always works; the first git *operation* raises a
  precise `GitNotAvailableError`. Use `is_git_available()` to feature-detect.
- **Git LFS** is a further prerequisite for *efficient* binary versioning. Without
  it, `init` warns once and the `.3dc` commits as an ordinary (large) blob — still
  valid, just heavier. `include_binary=False` allows JSONL-only commits.
- **Float drift across environments**: the codec is bit-exact, but the same model
  on a different machine/cadwork build may report slightly different floats →
  spurious diffs. Commit from a consistent environment.
- **Merge conflicts** are surfaced, never auto-resolved: `pull` raises
  `MergeConflictError`; conflict markers in the JSONL make `restore` raise
  `CodecError`. The binary `.3dc` can't be line-merged — resolve in git, then
  reopen.

The codec is pure (stdlib only) and the whole stack is testable with no git via
the `Repository` seam. A runnable, CI-safe tour (backed by a fake repository)
lives in [`examples/versioning.py`](../examples/versioning.py).

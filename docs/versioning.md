# Versioning: a git workflow over the model

A cadwork model is a binary `.3d` / `.3dc` — git can store it but cannot *diff* it.
`pycadwork.versioning` adds a real git workflow (commit / branch / checkout /
push / pull) **plus** a machine-readable serialization so changes are reviewable.
It is a thin bridge between three existing pieces:

```text
model  ⇄  ModelSnapshot     (reuses pycadwork.persistence)
       ⇄  diffable JSONL     (SnapshotCodec — deterministic, PK-sorted, one object/line)
       ⇄  git                (Repository seam; GitRepository over GitPython, lazy-loaded)
```

A `commit` **losslessly** captures the model as *both* a per-table JSONL tree
(the reviewable, line-diffable artifact) and the saved `.3d` / `.3dc` tracked via
**Git LFS** (the full-fidelity artifact a checkout restores for reopening in cadwork).

```python
from pycadwork.versioning import ModelVersioning

vcs = ModelVersioning.open()                 # repo in the active .3dc's directory
report = vcs.commit("framed the north wall") # saves .3dc + writes JSONL + commits
print(report.commit.sha, report.files_changed, report.document_file)

vcs.create_branch("alternative-roof")        # ordinary git branching
...
report = vcs.switch_to("main")               # checkout + load the model, in one step
print(report.total)                          # elements now in the live model
```

### Bringing a version into the live model

`switch_to(ref)` is the real "git checkout this version": it checks out `ref`
(swapping the tracked files on disk) **and** loads that version's committed
`.3dc` into the running cadwork model. `reload_model()` does just the load half
(after a plain `checkout`). Both are full-fidelity — real geometry for every
element type, **including element moves** — and both default to a **smart**
switch that behaves like a real `git checkout`: only what actually changed
churns.

```python
vcs.checkout("main")          # git files only — the live model is untouched
report = vcs.reload_model()   # now load main's committed .3dc into the model
```

#### Smart switching: minimal-touch, like real `git checkout`

By default (`strategy="smart"`) a switch reconciles the live model against the
target by **content fingerprint** — never by id or GUID, since
`file_controller.import_3dc_file` is additive-only and mints a fresh id *and*
a fresh cadwork GUID for everything it imports. An element whose content
didn't change keeps its existing cadwork id/GUID untouched; only the true
delta is added or removed. A pure-removal switch (nothing new to bring in)
never even imports the binary. `reload_model()` / `switch_to()` return a
`SmartSwitchReport(document_path, unchanged, added, removed, total)`.

```python
report = vcs.switch_to("main")   # smart by default
print(report.unchanged, report.added, report.removed, report.total)
```

`preview_switch(ref)` classifies the live model against `ref`'s committed
snapshot **without checking anything out** (it reads the target's JSONL
straight out of git); `sync_status()` does the same against the currently
checked-out version. Both return a `SyncPlan(unchanged, stale, missing)` — a
pure, no-mutation preview, the smart-switch analogue of `model_status()`.

```python
plan = vcs.preview_switch("main")   # still on the current branch
print(len(plan.unchanged), len(plan.stale), len(plan.missing))
```

Pass `strategy="full"` to `reload_model()` / `switch_to()` for the original,
simpler behavior: every live element is deleted and the whole committed
`.3dc` is imported, so *every* element gets a fresh cadwork id/GUID
regardless of whether it changed. Returns the original `ReloadReport`. Use
this when a clean id/GUID reset is actually what you want.

```python
report = vcs.switch_to("main", strategy="full")
print(report.imported)
```

**Identity contract.** `element.jsonl`'s `cadwork_guid` column is pycadwork's
git-object-equivalent identity: it is git-diffable, persistent across
ordinary edits, and is what the smart switch's GUID fast path matches on.
There is no separate index file — this existing column *is* the lookup.

**Container atomicity.** A container's fingerprint folds in the sorted
multiset of its members' own fingerprints, so a change to *any* member (or to
the container itself) changes the container's own fingerprint too. When a
container is classified as changed, every one of its current members is swept
into the "stale" set as well — even one whose own content is byte-identical —
because a preserved member can't be surgically grafted into a freshly
re-imported container without orphaning it. **Consequence:** a container is
atomic for change detection — if the container or any one member changes, the
whole group is treated as one changed unit and re-brought-in together. Still
strictly better than the pre-smart-switch behavior, where the *entire model*
churned on every switch regardless of strategy.

`restore()` (alias `load()`) is the lower-level form: it returns the working-tree
`.3dc` path (e.g. to reopen by hand on another machine). `restore(apply_to_model=True)`
*additionally* runs a **legacy best-effort** JSON write-back through the
persistence `ModelWriter`; per its limits, existing elements' points are **never
moved** and non-reconstructable types are skipped (counted in
`RestoreReport.skipped`) — so it cannot reproduce a move. Prefer `reload_model`
for a faithful restore; the JSON write-back's one advantage is that it carries
project-level metadata (see limitations). `model_status()` is a pure preview —
`diff(live model, working-tree snapshot)` — needing no git.

**Limits of the binary reload:** `import_3dc_file` brings in *elements*, not
project-level metadata (name/number/architect…). With `strategy="full"` this
means fresh ids/GUIDs for the *whole model*; with the default
`strategy="smart"` the scope narrows to only the elements that actually
changed (see container atomicity above). A version committed without its
binary (`include_binary=False`) has nothing to reload — `reload_model` raises
`RepositoryError` either way.

## Honest limitations

Stated in the docstrings too:

- **GitPython is an optional extra** (`pip install 'pycadwork[git]'`) and a `git`
  executable is required at runtime — both are often absent inside cadwork.
  `import pycadwork.versioning` always works; the first git *operation* raises a
  precise `GitNotAvailableError`. Use `is_git_available()` to feature-detect.
- **Git LFS** is a further prerequisite for *efficient* binary versioning. Without
  it, `init` warns once and the `.3d` / `.3dc` commits as an ordinary (large) blob — still
  valid, just heavier. `include_binary=False` allows JSONL-only commits.
- **Float drift across environments**: the same model on a different
  machine/cadwork build may report floats differing by 1–2 ULP in their
  least-significant bits. To stop these from showing as spurious, never-resolving
  diffs, the codec quantizes every float to 12 significant digits on write
  (`FLOAT_SIGNIFICANT_DIGITS`) — scale-invariant, so it absorbs drift in large
  volumes as well as in coordinates while preserving sub-micron precision at
  building scale. Reads stay faithful to what is on disk; tune via
  `SnapshotCodec(float_significant_digits=…)`.
- **Merge conflicts** are surfaced, never auto-resolved: `pull` raises
  `MergeConflictError`; conflict markers in the JSONL make `restore` raise
  `CodecError`. The binary `.3dc` can't be line-merged — resolve in git, then
  reopen.

The codec is pure (stdlib only) and the whole stack is testable with no git via
the `Repository` seam. A runnable, CI-safe tour (backed by a fake repository)
lives in [`examples/versioning.py`](../examples/versioning.py).

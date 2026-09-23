# Spec: Git-like model versioning (model-aware defaults)

## Problem Statement

Cadwork users who know git expect versioning verbs (`checkout`, `pull`, `merge`)
to update the **working artifact**. In `pycadwork.versioning` those verbs only
swap files on disk; the live 3d model stays on the previous version until a
separate `switch_to` / `reload_model` / “Load model to version” step. That dual
mental model is documented as a surprise, taught inconsistently across examples,
and makes the dock UI talk like a two-phase tool rather than a git client for
models.

## Solution

**Breaking re-semantics** on `ModelVersioning` so the primary verbs are
model-aware by default:

- `checkout`, `pull`, and `merge` update git **and** load the resulting version
  into the live model (smart strategy by default).
- Pure-git behavior remains available via `apply_to_model=False`.
- If the live model differs from the currently checked-out committed snapshot
  (`sync_status` has any `stale` or `missing`), model-loading operations **refuse**
  unless `force=True` (or the dock confirms, which passes `force=True`).
- `switch_to` becomes a thin alias of model-aware `checkout` (kept for
  compatibility).
- Align the dock widget, all versioning examples, and `docs/versioning.md` with
  the new defaults.
- Add a real-cadwork integration test that launches the fixture model via
  `pycadwork.terminal` (`open … --run-program …`) and proves a commit → branch →
  edit → switch-back loop.

## User Stories

1. **As a** CAD engineer using versioning inside cadwork, **I want** switching
   branch to bring that branch’s model into the viewport, **so that** I do not
   have to remember a second “load model” step after every checkout.

2. **As a** CAD engineer, **I want** `pull` and `merge` to leave me on the
   resulting model when they succeed, **so that** collaboration matches the
   “update then continue modeling” habit from git UIs.

3. **As a** CAD engineer with uncommitted live edits, **I want** a switch/pull/
   merge that would discard those edits to fail loudly unless I force it, **so
   that** I do not silently lose work.

4. **As a** script author / test author, **I want** `apply_to_model=False` on
   checkout/pull/merge, **so that** pure working-tree operations stay available
   without going through `vcs.repository` for common cases.

5. **As a** user of the versioning dock, **I want** buttons and messages that
   match the model-aware defaults (no “now press Load model after pull”), **so
   that** the GUI feels like a model git client.

6. **As a** maintainer, **I want** an integration test over
   `timber-framed-slab.3d` driven by the terminal launcher, **so that** the
   real cadwork path is exercised when cadwork + git are installed and skipped
   cleanly otherwise.

7. **As a** reader of examples/docs, **I want** every versioning tutorial to
   teach the new defaults, **so that** the old “checkout does not touch the
   model” surprise is gone.

## Implementation Decisions

### API (breaking)

On `ModelVersioning`:

| Method | New default behavior | Escape hatches |
|--------|----------------------|----------------|
| `checkout(ref, *, apply_to_model=True, strategy="smart", force=False)` | Git checkout + `reload_model` when `apply_to_model` | `apply_to_model=False`; `strategy="full"`; `force=True` skips dirty guard |
| `pull(..., *, apply_to_model=True, strategy="smart", force=False)` | Git pull + reload when success and `apply_to_model` | same |
| `merge(..., *, apply_to_model=True, strategy="smart", force=False)` | Git merge + reload when success and `apply_to_model` | same |
| `switch_to(...)` | Alias of model-aware `checkout` (same kwargs) | same |
| `reload_model(...)` | Unchanged (loads current working-tree version) | `strategy`; dirty guard applies when used as “discard live edits to HEAD” path from dock — see below |

Return type for model-aware checkout/pull/merge: `ReloadReport | SmartSwitchReport | None`
— `None` when `apply_to_model=False` (file-only). Prefer a small union rather than
a new mega-report; document clearly.

**Dirty guard:** before any operation that would call `reload_model` (including
`reload_model` itself when used to discard live work — dock path), if
`sync_status()` reports any `stale` or `missing` elements and `force` is false,
raise **`DirtyWorkingTreeError`** (new subclass of `RepositoryError`) with a
message that names commit / force. Definition of dirty for this guard is
**live model vs currently checked-out committed snapshot**, not git index
dirtiness (`status().is_dirty` remains available separately for uncommitted
JSONL/binary tree changes).

**Order of operations for checkout:**

1. If `apply_to_model` and not `force`: dirty-guard against *current* HEAD snapshot
   (refuse losing live edits before leaving).
2. Optionally also preview target via `preview_switch` only for messaging — not
   required for the refuse rule (refuse is about uncommitted live delta vs current
   commit).
3. `_repo.checkout(ref)`.
4. If `apply_to_model`: `reload_model(strategy=…)`.

**Order for pull/merge:**

1. Dirty guard (same as above) when `apply_to_model` and not `force`.
2. `_repo.pull` / `_repo.merge` — on `MergeConflictError`, **do not** load model;
   re-raise.
3. If `apply_to_model`: `reload_model(strategy=…)`.

**`create_branch`:** remains git-only (new branch points at same commit; live
model already matches). No model load.

**`push` / `log` / `status` / `diff` / `commit`:** unchanged semantics.

**Exports:** add `DirtyWorkingTreeError` to `__init__.py` / `__all__`.

**Repository Protocol / GitRepository / FakeRepository:** no contract change
required for apply_to_model (facade-only). Update conflict error text that still
says “restore()/reopen” to “reload_model / resolve then checkout”.

### Dock (`examples/versioning_dock_widget.py`)

- Branch switch continues to preview + confirm; on accept call
  `checkout(..., force=True)` (user already confirmed) with strategy choice.
- Pull / merge: after success, model is already loaded — remove “Use Load model
  to version” copy; show smart-switch summary when a report is returned.
- “Load model to version” stays as explicit discard-to-HEAD (reload); confirm +
  `force=True`.
- Surface `DirtyWorkingTreeError` like other `RepositoryError`s if any path
  forgets `force`.

### Examples & docs

Update all of:

- `examples/versioning.py`
- `examples/versioning_in_cadwork.py`
- `examples/versioning_branch_workflow.py`
- `examples/versioning_dock_widget.py`
- `examples/versioning_session.py` (if present / still referenced)
- `docs/versioning.md`
- Package / module docstrings that still teach checkout-then-restore

Remove the “⚠️ checkout does not rewind the live model” framing; replace with
model-aware defaults + `apply_to_model=False` note.

### Integration test

- Location: e.g. `tests/versioning/test_cadwork_run_program.py` (or
  `tests/integration/…`).
- Host pytest: locate `ci_start` (reuse `find_ci_start` or soft-fail), require
  `is_git_available()`, copy fixture
  `tests/fixtures/model/timber-framed-slab.3d` to a temp work dir, write a
  small **run-program script** that:
  1. Opens/saves context as provided by cadwork,
  2. `ModelVersioning.open()` → `commit("baseline")`,
  3. `create_branch("feature/it")`, mutate a detectable element property or add a
     marker element, `commit("feature change")`,
  4. `checkout("main")` (default model-aware) and assert live model no longer has
     the feature change,
  5. Writes a JSON result file (pass/fail + counts) next to the temp dir.
- Host launches via terminal translation or direct argv:
  `ci_start <model> /RUNPROGRAM=<script> /NO-GUI` (prefer going through
  `ProcessLauncher` / CLI translation for fidelity).
- Assert process exit code 0 and result file `ok`.
- **`pytest.mark.skipif`** when `ci_start` or git/GitPython unavailable — never
  fail default CI for missing cadwork.
- Do **not** rely on autouse `FakeCadworkAdapter` for the in-cadwork script
  (script runs in cadwork’s interpreter). Host test only orchestrates process +
  files.

## Testing Decisions

| Layer | What | How |
|-------|------|-----|
| Unit (fake repo + fake cadwork) | New defaults: checkout loads model; `apply_to_model=False` does not; dirty raises; force proceeds; pull/merge load after success; conflict skips load | Extend `tests/versioning/test_versioning.py` + FakeRepository |
| Unit | `DirtyWorkingTreeError` is `RepositoryError` subclass; exported | Public surface / import test if needed |
| Real git (existing) | Unchanged skipif; conflict messages if touched | `test_git_integration.py` |
| Real cadwork IT | Fixture model round-trip | New test + skipif |
| Examples | Still import-safe where listed in `MODULES`; in-cadwork scripts not CI-tour | Existing `test_examples` patterns |

Fake-first remains the default development path; IT is optional enrichment.

## Out of Scope

- Stash, tags, rebase, cherry-pick, amend, worktrees
- Auto-resolving merge conflicts
- Changing the JSONL codec / fingerprint algorithm (unless a test forces a tiny fix)
- Dock QThread for network push/pull
- Requiring cadwork in CI

## Further Notes

- Prefer minimal churn in `_sync` / `_codec` — this plan is facade + UX + tests.
- Keep Windows open-file layout (live model ignored; binary under `model/`).
- Suggested plan slug: `git-like-model-versioning`.

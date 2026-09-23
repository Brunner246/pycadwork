# Seed: Dock, examples, and versioning docs

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 03
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** L2
- **Blocked by:** 01-facade-model-aware.md
- **Estimated size:** M
- **Priority:** High
- **Target repo:** `pycadwork`
- **Branch:** `feature/git-like-model-versioning-03-dock-examples-docs`

## Source documents

- **Spec:** `docs/spec/git-like-model-versioning.md`
- **Research:** `docs/research/git-like-model-versioning.md`
- **Architecture:** `docs/architecture/git-like-model-versioning.md`
- **Verification:** `docs/verification/git-like-model-versioning.md`

## Scope (Definition of Ready)

Align the versioning dock widget, **all** versioning examples, package/module
docstrings that teach the old surprise, and `docs/versioning.md` with
model-aware defaults (US-5, US-7). Remove “checkout does not rewind the live
model” framing; document `apply_to_model=False` and dirty/`force` behavior.

## Spec guardrail

**In scope (verbatim):**

> Align the dock widget, all versioning examples, and `docs/versioning.md` with the new defaults. Update `examples/versioning.py`, `versioning_in_cadwork.py`, `versioning_branch_workflow.py`, `versioning_dock_widget.py`, `versioning_session.py` (if present), package/module docstrings. Remove the “⚠️ checkout does not rewind the live model” framing.

**Out of scope (verbatim):**

> Facade implementation (seed 01). Real-cadwork IT (seed 02). Dock QThread for push/pull. Stash/tags/rebase.

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** examples/dock call `ModelVersioning` only (no new domain layer)
- **Driven port(s) + test double:** none new
- **Deep module(s):** none — presentation/docs only
- **SOLID / cross-cutting:** Dock keeps MVVM; ViewModel catches `RepositoryError` (includes `DirtyWorkingTreeError`); confirm dialogs pass `force=True`
- **Out of scope (architecture §7):** QThread worker architecture for the dock

## Reusable building blocks

- Seed 01 public API (`checkout` model-aware, `DirtyWorkingTreeError`, reports)
- `examples/versioning_dock_widget.py` MVVM structure — keep layers
- `docs/versioning.md` — rewrite mental model section

## Touched files (predicted)

```
- examples/versioning_dock_widget.py
- examples/versioning.py
- examples/versioning_in_cadwork.py
- examples/versioning_branch_workflow.py
- examples/versioning_session.py (if present)
- docs/versioning.md
- src/pycadwork/versioning/__init__.py (package docstring only, if not done in 01)
- src/pycadwork/versioning/_versioning.py (module docstring only if still teaching old model)
```

## Acceptance criteria

- [ ] Dock pull/merge success copy no longer tells user to press “Load model to version”
- [ ] Branch switch / reload confirms then calls model-aware APIs with `force=True`
- [ ] Branch workflow example uses model-aware checkout (not legacy restore-after-checkout as the main path)
- [ ] `docs/versioning.md` documents defaults + escape hatches
- [ ] Forbidden old-surprise wording removed from examples/docs (verification US-7)
- [ ] CI example tour still green: `uv run pytest tests/test_examples.py -q` (as applicable)
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/test_examples.py tests/versioning/ -q`
- **Runtime exercise:** same for import-safe examples
- **Inner-loop:** `uv run pytest tests/test_examples.py -q`
- **Graphical / Manual:** optional human dock smoke inside cadwork (non-blocking)

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Confirm seed 01 Done so examples call the new API.
3. Run implement on this seed’s branch.

```
/lp-to-implement @docs/sessions/git-like-model-versioning/03-dock-examples-docs.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/git-like-model-versioning/03-dock-examples-docs.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

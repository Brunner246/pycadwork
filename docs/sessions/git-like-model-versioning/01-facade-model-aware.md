# Seed: Facade model-aware re-semantics + unit tests

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 01
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** L1
- **Blocked by:** None — Ready
- **Estimated size:** L
- **Priority:** Highest
- **Target repo:** `pycadwork`
- **Branch:** `feature/git-like-model-versioning-01-facade-model-aware`

## Source documents

- **Spec:** `docs/spec/git-like-model-versioning.md`
- **Research:** `docs/research/git-like-model-versioning.md`
- **Architecture:** `docs/architecture/git-like-model-versioning.md`
- **Verification:** `docs/verification/git-like-model-versioning.md`

## Scope (Definition of Ready)

Implement breaking model-aware defaults on `ModelVersioning` for `checkout` /
`pull` / `merge`, dirty-live-model guard with `DirtyWorkingTreeError` and
`force=`, pure-git escape hatch `apply_to_model=False`, `switch_to` as alias,
public exports, and full fake-backed unit coverage (US-1–4).

## Spec guardrail

**In scope (verbatim):**

> Breaking re-semantics on `ModelVersioning` so the primary verbs are model-aware by default: `checkout`, `pull`, and `merge` update git **and** load the resulting version into the live model (smart strategy by default). Pure-git via `apply_to_model=False`. Dirty live model vs checked-out snapshot refuses unless `force=True`. `switch_to` becomes a thin alias of model-aware `checkout`.

**Out of scope (verbatim):**

> Stash, tags, rebase, cherry-pick, amend, worktrees. Auto-resolving merge conflicts. Changing the JSONL codec / fingerprint algorithm (unless a test forces a tiny fix). Dock QThread. Requiring cadwork in CI. Examples/docs/dock (seed 03). Real-cadwork IT (seed 02).

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** conceptual `ModelVersioning` public surface (no new Protocol)
- **Driven port(s) + test double:** `Repository` + `FakeRepository`; cadwork via existing `FakeCadworkAdapter`
- **Deep module(s):** `ModelVersioning` only — policy on the facade
- **SOLID / cross-cutting (verbatim):** `DirtyWorkingTreeError(RepositoryError)` — refuse load when live model has stale/missing vs checked-out snapshot and `force=False`. MergeConflictError — still no model load after conflict. Repository Protocol unchanged.
- **Out of scope (architecture §7):** New VersioningService Protocol; stash/tag ports; smart-switch inside Repository; dock QThread

If this slice needs a `[NEW]` architectural decision, STOP and run `/lp-to-architecture` first.

## Reusable building blocks

- `src/pycadwork/versioning/_versioning.py` — facade methods to re-semanticize
- `src/pycadwork/versioning/_sync.py` — `classify` / `SyncPlan` for dirty guard via `sync_status`
- `src/pycadwork/versioning/_repository.py` — error hierarchy to extend
- `tests/_fakes/repository.py` — fake-backed tests
- `tests/versioning/test_versioning.py` — patterns for commit/branch/switch tests

## Touched files (predicted)

```
- src/pycadwork/versioning/_versioning.py — checkout/pull/merge kwargs, dirty guard, switch_to alias
- src/pycadwork/versioning/_repository.py — DirtyWorkingTreeError
- src/pycadwork/versioning/__init__.py — export DirtyWorkingTreeError
- src/pycadwork/versioning/_git.py — conflict message wording only if needed
- tests/versioning/test_versioning.py — new defaults / dirty / force / apply_to_model=False / pull-merge load
- tests/test_public_surface.py — if public surface is asserted
```

## Acceptance criteria

- [ ] `checkout` / `pull` / `merge` default to loading the live model (smart)
- [ ] `apply_to_model=False` leaves the live model untouched; returns `None`
- [ ] Dirty live model raises `DirtyWorkingTreeError` unless `force=True`
- [ ] `MergeConflictError` paths do not call reload
- [ ] `switch_to` aliases model-aware `checkout`
- [ ] `DirtyWorkingTreeError` exported from `pycadwork.versioning`
- [ ] Tests with fakes from architecture §5
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/versioning/ -q`
- **Runtime exercise:** `uv run pytest tests/versioning/test_versioning.py -q`
- **Inner-loop:** `uv run pytest tests/versioning/test_versioning.py -k "checkout or dirty or pull or merge or apply_to_model" -q`
- **Graphical / Manual:** none

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Run implement — it switches to this seed’s `**Branch:**` itself.
3. You own commits and pushes on this seed branch (plugin does not push seed branches).

```
/lp-to-implement @docs/sessions/git-like-model-versioning/01-facade-model-aware.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/git-like-model-versioning/01-facade-model-aware.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

# Seed: Capstone verification

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 04
- **Type:** AFK
- **Headless:** true
- **Capstone:** true
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** Lf1
- **Blocked by:** 01-facade-model-aware.md, 02-cadwork-it.md, 03-dock-examples-docs.md
- **Estimated size:** S
- **Priority:** Medium
- **Target repo:** `pycadwork`
- **Branch:** `feature/git-like-model-versioning-04-capstone`

## Source documents

- **Spec:** `docs/spec/git-like-model-versioning.md`
- **Research:** `docs/research/git-like-model-versioning.md`
- **Architecture:** `docs/architecture/git-like-model-versioning.md`
- **Verification:** `docs/verification/git-like-model-versioning.md`

## Scope (Definition of Ready)

Run the whole-feature acceptance recipe from verification §5a. No production
feature code. Fix only regressions that block GREEN if they are clearly in-scope
for this plan; otherwise file residual notes on the BOARD revision log.

## Spec guardrail

**In scope (verbatim):**

> Capstone proves US-1–7 via the verification contract: versioning unit suite, example tour, optional cadwork IT (skip-or-green), full pytest no-regression.

**Out of scope (verbatim):**

> New features. Architecture expansion. HITL dock polish beyond what seeds 01–03 delivered.

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

> Capstone/Interim/Integration: verification-first — no production feature code; no `[NEW]` architecture.

- **Driving port(s):** n/a
- **Driven port(s) + test double:** n/a
- **Deep module(s):** n/a
- **SOLID / cross-cutting (verbatim):** n/a
- **Out of scope (architecture §7):** all product work

## Reusable building blocks

- Verification §2–§5a commands
- All prior seed deliverables on the feature branch

## Touched files (predicted)

```
- (no paths predictable yet — overlap detection skipped for this seed)
```

## Acceptance criteria

- [x] `uv run pytest tests/versioning/ tests/test_examples.py -q` GREEN
- [x] IT module skip-or-green: `uv run pytest tests/versioning/test_cadwork_run_program.py -v`
- [x] No-regressions: `uv run pytest -q` GREEN (IT skip counts as green)
- [x] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest -q`
- **Runtime exercise:** `uv run pytest tests/versioning/ tests/test_examples.py -q`
- **Inner-loop:** `uv run pytest tests/versioning/ -q`
- **Graphical / Manual:** optional dock HITL — non-blocking

## First steps for this session

1. Ensure seeds 01–03 are Done and integrated on the feature branch.
2. Run the capstone commands; fix only plan-scoped regressions.
3. Mark BOARD card Done when GREEN.

```
/lp-to-implement @docs/sessions/git-like-model-versioning/04-capstone.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/git-like-model-versioning/04-capstone.md @docs/sessions/git-like-model-versioning/BOARD.md @docs/spec/git-like-model-versioning.md @docs/architecture/git-like-model-versioning.md
```

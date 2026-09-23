# Seed: Capstone verification

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 03
- **Type:** AFK
- **Headless:** true
- **Capstone:** true
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** Lf1
- **Blocked by:** 01-work-unit.md, 02-docs-examples.md
- **Estimated size:** S
- **Priority:** Medium
- **Target repo:** `pycadwork`
- **Branch:** `feature/work-units-03-capstone`

## Source documents

- **Spec:** `docs/spec/work-units.md`
- **Research:** `docs/research/work-units.md`
- **Architecture:** `docs/architecture/work-units.md`
- **Verification:** `docs/verification/work-units.md`

## Scope (Definition of Ready)

Run the whole-feature acceptance recipe from verification §5a. No production
feature code. Fix only regressions that block GREEN if they are clearly in-scope
for this plan; otherwise file residual notes on the BOARD revision log.

## Spec guardrail

**In scope (verbatim):**

> Capstone proves US-1–8 via the verification contract: `tests/work/`, example tour, public-surface exports, isolation, full pytest no-regression. Headless-only; no real-cadwork Ctrl+Z.

**Out of scope (verbatim):**

> New features. Architecture expansion. Compensating geometry. `make_undo`. CSV export. HITL cadwork Undo smoke.

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

- [ ] `uv run pytest tests/work/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q` GREEN
- [ ] No-regressions: `uv run pytest -q` GREEN
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest -q`
- **Runtime exercise:** `uv run pytest tests/work/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q`
- **Inner-loop:** `uv run pytest tests/work/ -q`
- **Graphical / Manual:** none

## First steps for this session

1. Ensure seeds 01–02 are Done and integrated on the feature branch.
2. Run the capstone commands; fix only plan-scoped regressions.
3. Mark BOARD card Done when GREEN.

```
/lp-to-implement @docs/sessions/work-units/03-capstone.md @docs/sessions/work-units/BOARD.md @docs/spec/work-units.md @docs/architecture/work-units.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/work-units/03-capstone.md @docs/sessions/work-units/BOARD.md @docs/spec/work-units.md @docs/architecture/work-units.md
```

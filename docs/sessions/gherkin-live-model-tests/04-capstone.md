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
- **Blocked by:** 01-ifc-snapshot.md, 02-gherkin-runner.md, 03-docs-examples.md
- **Estimated size:** S
- **Priority:** Medium
- **Target repo:** `pycadwork`
- **Branch:** `feature/gherkin-live-model-tests-04-capstone`

## Source documents

- **Spec:** `docs/spec/gherkin-live-model-tests.md`
- **Research:** `docs/research/gherkin-live-model-tests.md`
- **Architecture:** `docs/architecture/gherkin-live-model-tests.md`
- **Verification:** `docs/verification/gherkin-live-model-tests.md`

## Scope (Definition of Ready)

Run the whole-feature acceptance recipe from verification §5a. No production
feature code. Fix only regressions that block GREEN if they are clearly in-scope
for this plan; otherwise file residual notes on the BOARD revision log.

## Spec guardrail

**In scope (verbatim):**

> Capstone proves US-1–11 via the verification contract: `tests/gherkin/`, rule factories, `attrs.ifc_type`, persistence/versioning IFC, example tour, public-surface exports, isolation, full pytest no-regression. Headless-only; no real-cadwork IFC IT.

**Out of scope (verbatim):**

> New features. Architecture expansion. pytest-bdd. Cadwork CLI. Mutating `When`. HITL cwapi3d IFC stringify smoke.

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

- [ ] `uv run pytest tests/gherkin/ tests/rules/test_library.py tests/rules/test_engine.py tests/element/test_attributes.py tests/persistence/ tests/versioning/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q` GREEN
- [ ] No-regressions: `uv run pytest -q` GREEN
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest -q`
- **Runtime exercise:** `uv run pytest tests/gherkin/ tests/rules/test_library.py tests/rules/test_engine.py tests/element/test_attributes.py tests/persistence/ tests/versioning/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q`
- **Inner-loop:** `uv run pytest tests/gherkin/ -q`
- **Graphical / Manual:** none

## First steps for this session

1. Ensure seeds 01–03 are Done and integrated on the feature branch.
2. Run the capstone commands; fix only plan-scoped regressions.
3. Mark BOARD card Done when GREEN.

```
/lp-to-implement @docs/sessions/gherkin-live-model-tests/04-capstone.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/gherkin-live-model-tests/04-capstone.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

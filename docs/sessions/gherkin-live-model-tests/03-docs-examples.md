# Seed: Module README, example feature, listings

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 03
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** L3
- **Blocked by:** 02-gherkin-runner.md
- **Estimated size:** M
- **Priority:** High
- **Target repo:** `pycadwork`
- **Branch:** `feature/gherkin-live-model-tests-03-docs-examples`

## Source documents

- **Spec:** `docs/spec/gherkin-live-model-tests.md`
- **Research:** `docs/research/gherkin-live-model-tests.md`
- **Architecture:** `docs/architecture/gherkin-live-model-tests.md`
- **Verification:** `docs/verification/gherkin-live-model-tests.md`

## Scope (Definition of Ready)

Teach Gherkin live-model tests the way every other pycadwork module is taught:
`docs/gherkin.md` (the module README), `examples/gherkin.py` plus
`examples/features/framing.feature` on the CI example tour, listing rows, and
rules/elements docs for the new factories and `attrs.ifc_type`.

Do not add `src/pycadwork/gherkin/README.md`. Do not change runner behaviour.

## Spec guardrail

**In scope (verbatim):**

> `docs/gherkin.md` is the module README: dialect, closed phrases, `run_features`, `register_step`, IFC canonical strings, live vs fake. First screenful: this compiles to `pycadwork.rules` and does not replace it. Document the live-adapter verification gap (no `/RUNPROGRAM` IFC IT in v1). `docs/rules.md` rows for new factories. `docs/elements.md` `attrs.ifc_type`. `docs/architecture.md` package-layout row + mermaid node. `docs/README.md` / `README.md` / `examples/README.md` rows. `examples/gherkin.py` seeds a small fake model, runs the `.feature`, shows pass and fail. `examples/features/framing.feature` asserts name/material, dimensions, and IFC type. Append `"gherkin"` to `MODULES`.

**Out of scope (verbatim):**

> Changing `run_features` behaviour. `src/pycadwork/gherkin/README.md`. pytest-bdd tutorial. Cadwork menu/CLI tutorial. Real-cadwork IFC IT. Rewriting `docs/rules.md` beyond the new factory rows.

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** existing `run_features` (seed 02) and `attrs.ifc_type` (seed 01)
- **Driven port(s) + test double:** autouse fake via `tests/test_examples.py`
- **Deep module(s):** none new — teaching assets only
- **SOLID / cross-cutting (verbatim):** Document in `docs/gherkin.md`, in the first screenful, that this compiles to `pycadwork.rules` and does not replace it. Document architecture §5 runtime-verification gap.
- **Out of scope (architecture §7):** all product-code expansion

If this slice needs a `[NEW]` architectural decision, STOP and run `/lp-to-architecture` first.

## Reusable building blocks

- `docs/rules.md` — module-doc tone and factory table
- `examples/rules.py` — `demo_*` + `run()` shape
- `examples/__init__.py` — `MODULES` tuple (append `"gherkin"`)
- `examples/README.md`, `docs/README.md`, `README.md` — table row pattern
- `docs/architecture.md` — mermaid + package layout table
- Seed 01/02 public API — examples import only from `pycadwork`

## Touched files (predicted)

```
- docs/gherkin.md — module README
- docs/rules.md — new factory rows
- docs/elements.md — attrs.ifc_type
- docs/README.md — Working with the model bullet
- docs/architecture.md — mermaid node + layout row
- README.md — documentation table row
- examples/gherkin.py — seed model, run feature, show pass/fail
- examples/features/framing.feature — success-demo feature
- examples/__init__.py — MODULES += "gherkin"
- examples/README.md — table row
```

## Acceptance criteria

- [ ] `docs/gherkin.md` exists, opens with compile-to-rules, shows dialect, closed phrases, `run_features`, IFC strings, live vs fake
- [ ] `examples.gherkin.run()` completes under the fake (`tests/test_examples.py -k gherkin`)
- [ ] `"gherkin"` is in `examples.MODULES`
- [ ] `examples/features/framing.feature` asserts material, dimensions, and IFC type
- [ ] README / docs/README / examples/README / architecture layout mention `pycadwork.gherkin`
- [ ] `docs/rules.md` lists the new factories; `docs/elements.md` documents `attrs.ifc_type`
- [ ] No `src/pycadwork/gherkin/README.md`
- [ ] Tests with fakes from architecture §5 (example tour)
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/test_examples.py tests/gherkin/ -q`
- **Runtime exercise:** `uv run pytest tests/test_examples.py -k gherkin` — US-9
- **Inner-loop:** `uv run pytest tests/test_examples.py -k gherkin`
- **Graphical / Manual:** none

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Run implement — it switches to this seed’s `**Branch:**` itself.
3. You own commits and pushes on this seed branch (plugin does not push seed branches).

```
/lp-to-implement @docs/sessions/gherkin-live-model-tests/03-docs-examples.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/gherkin-live-model-tests/03-docs-examples.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

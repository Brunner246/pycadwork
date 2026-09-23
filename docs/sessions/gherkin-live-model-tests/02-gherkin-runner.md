# Seed: Gherkin parser, compiler, run_features

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 02
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** L2
- **Blocked by:** 01-ifc-snapshot.md
- **Estimated size:** L
- **Priority:** High
- **Target repo:** `pycadwork`
- **Branch:** `feature/gherkin-live-model-tests-02-gherkin-runner`

## Source documents

- **Spec:** `docs/spec/gherkin-live-model-tests.md`
- **Research:** `docs/research/gherkin-live-model-tests.md`
- **Architecture:** `docs/architecture/gherkin-live-model-tests.md`
- **Verification:** `docs/verification/gherkin-live-model-tests.md`

## Scope (Definition of Ready)

Add `pycadwork.gherkin`: stdlib dialect parser, built-in Then catalog,
`register_step` / `reset_steps`, compiler to `Rule`s, `run_features` →
`FeatureReport`. Compile closed phrases at `Severity.ERROR` through
`rules.check` once; map `Violation`s back by `rule_id`. Dimension steps fail
on missing geometry; `every …` with zero matches is ERROR. Unmatched `When`
and unknown steps raise `GherkinError` before `check`. Re-export runner types.
Tests under `tests/gherkin/` for US-1, US-2, US-3 (phrase), US-4, US-5, US-6,
US-7, US-8.

Do not write `docs/gherkin.md` or the example tour files (seed 03).

## Spec guardrail

**In scope (verbatim):**

> `run_features(snapshot, source) -> FeatureReport`. `source` is a path or feature text (newline or starts with `Feature:`). Dialect: Feature, Background, Scenario, Scenario Outline, Given/When/Then/And/But, Examples tables, `#` comments. Reject tags, doc strings, `language:`, `Rule:` with line-numbered `GherkinError`. `Given the model` / `Given the snapshot` is a no-op. Closed Then vocabulary as Spec table; compiled ERROR. Zero matches for `every …` fail; `there are 0 …` is the empty assert. Dimension steps fail when geometry is missing (do not change `dimensions_within` itself). `register_step(pattern, factory)`; `reset_steps()` restores builtins. One `check` pass; `rule_id` encodes `feature:scenario:step-index` [+ outline row]. `FeatureReport.ok` when every scenario is ok.

**Out of scope (verbatim):**

> Official `gherkin` package / pytest-bdd / behave. pytest plugin auto-collection. Cadwork CLI / menu. Mutating `When` in the closed catalog. German keywords. Tags, hooks, doc strings. Module README, `examples/gherkin.py`, `examples/features/framing.feature` (seed 03). Changing IFC adapter or schema (seed 01).

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** `run_features`, `register_step`, `reset_steps`, `FeatureReport` / `GherkinError`
- **Driven port(s) + test double:** `rules.check` (pure) + snapshot literals; no cadwork import
- **Deep module(s):** `pycadwork.gherkin` (architecture §3.1); report DTOs (§3.2)
- **SOLID / cross-cutting (verbatim):** `pycadwork.gherkin` must not import `cadwork`, `bim_controller`, or `pycadwork.cadwork_adapter`. `pycadwork.rules` must not import `pycadwork.gherkin`. Assertion failures are data on `FeatureReport`, never raised. `register_step` is process-global; tests call `reset_steps` in teardown. New phrases via `register_step`, not by editing `run_features`.
- **Out of scope (architecture §7):** `GherkinPort` Protocol; folding parser into rules; pytest-bdd; CLI; mutating `When`; non-English keywords

If this slice needs a `[NEW]` architectural decision, STOP and run `/lp-to-architecture` first.

## Reusable building blocks

- Seed 01 factories: `ifc_type_is`, `material_is`, `count_is`, `all_of`, `named_equals`
- `src/pycadwork/rules/engine.py` — `check`, `for_types`, `ElementRule`
- `src/pycadwork/rules/library.py` — `dimensions_within` (wrap at compile)
- `src/pycadwork/rules/records.py` — `.ok` semantics
- `src/pycadwork/persistence/records.py` — snapshot literals
- `tests/rules/test_library.py` — `_snapshot` helper pattern
- `tests/test_public_surface.py` — `WORK_EXPORTS` pattern for `GHERKIN_EXPORTS`
- `tests/test_isolation.py`

## Touched files (predicted)

```
- src/pycadwork/gherkin/__init__.py — run_features, register_step, reset_steps, types
- src/pycadwork/gherkin/parser.py — dialect
- src/pycadwork/gherkin/ast.py — feature/scenario/step nodes
- src/pycadwork/gherkin/compile.py — steps → Rules
- src/pycadwork/gherkin/steps.py — built-in catalog
- src/pycadwork/gherkin/report.py — FeatureReport, ScenarioResult, StepFailure, GherkinError
- src/pycadwork/__init__.py — Gherkin re-exports
- tests/gherkin/__init__.py
- tests/gherkin/test_parser.py
- tests/gherkin/test_compile.py
- tests/gherkin/test_run.py
- tests/test_public_surface.py — GHERKIN_EXPORTS
```

## Acceptance criteria

- [ ] Closed Then phrases for material, group, IFC, exact/range dimensions, counts pass/fail snapshot literals as Spec
- [ ] Missing geometry on a dimension step is ERROR; zero-match `every …` is ERROR; `there are 0 …` passes on empty
- [ ] `run_features` maps violations onto scenario/step; `.ok` false on ERROR; empty feature is `.ok`
- [ ] Same feature text over a literal snapshot and a SQL `load_snapshot` yields equal `violations`
- [ ] Scenario Outline expands; Background prepends; `And`/`But` inherit kind
- [ ] Unknown `Then` and unmatched `When` raise `GherkinError` containing the raw step text
- [ ] Tags / doc strings / `language:` rejected with line number
- [ ] `register_step` adds a phrase; `reset_steps` restores builtins
- [ ] `GHERKIN_EXPORTS` on `pycadwork` and in `__all__`
- [ ] Isolation green (`pycadwork.gherkin` does not import `cadwork` / `*_controller`)
- [ ] Tests with fakes / literals from architecture §5
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/gherkin/ tests/test_public_surface.py tests/test_isolation.py -q`
- **Runtime exercise:** `uv run pytest tests/gherkin/ -q` — US-1–8 (phrase + report + inject + catalog + errors)
- **Inner-loop:** `uv run pytest tests/gherkin/test_run.py tests/gherkin/test_compile.py -q`
- **Graphical / Manual:** none

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Run implement — it switches to this seed’s `**Branch:**` itself.
3. You own commits and pushes on this seed branch (plugin does not push seed branches).

```
/lp-to-implement @docs/sessions/gherkin-live-model-tests/02-gherkin-runner.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/gherkin-live-model-tests/02-gherkin-runner.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

# Verification: Gherkin live-model tests

> **Source Spec:** `docs/spec/gherkin-live-model-tests.md`
> **Source research:** `docs/research/gherkin-live-model-tests.md`
> **Source architecture:** `docs/architecture/gherkin-live-model-tests.md`
> **Status:** Draft
>
> Owns the **verification-evidence** layer only. It cites Spec `## Testing Decisions`
> (testing intent) and architecture `## 5` (test doubles) — it never re-decides them.

## 1. Context

Correctness is behavioral on a new driving adapter: a `.feature` file plus a
`ModelSnapshot` either yields `FeatureReport.ok is True` with empty failures,
or names the scenario, step, and element that missed an attribute, dimension,
or IFC type. Architecture §5 says Gherkin tests use snapshot literals and IFC
adapter tests use the shipped `FakeCadworkAdapter`; Spec Testing Decisions say
no real-cadwork IFC IT in v1. Proof is therefore exact pytest assertions on
parse/compile/report, rule factories, fake `attrs.ifc_type`, SQL ADD COLUMN,
versioning fingerprints, isolation, public exports, and the example tour — the
harness already exists.

## 2. Per-story acceptance methodology

| Spec story | Acceptance check (what you run) | Observable signal | Judging method | Factory scope |
|-----------|----------------------------------|-------------------|----------------|---------------|
| US-1: attribute phrases in a `.feature` | `uv run pytest tests/gherkin/ -k "material or group or named"` | Feature with `Then every beam named "Stud" has material "Pine"` is `.ok` on a matching snapshot and not `.ok` when material is empty/`"Oak"`; `StepFailure.element_id` is the failing beam | `exact` | `repo-local` |
| US-2: dimension phrases (exact and range) | `uv run pytest tests/gherkin/ -k dimension` | `has width 80` passes at 80, fails at 81; `between 70 and 90` passes at 80; missing geometry satellite is ERROR (not a skip) | `exact` | `repo-local` |
| US-3: IFC type phrase | `uv run pytest tests/gherkin/ -k ifc tests/rules/test_library.py -k ifc_type` | `has ifc type "IfcBeam"` passes when `AttributeRecord.ifc_type == "IfcBeam"`; empty/`"IfcWall"` fails | `exact` | `repo-local` |
| US-4: `run_features` structured report | `uv run pytest tests/gherkin/test_run.py` | Failures carry `scenario`, `step`, `element_id`, `message`; `.ok` is False on any ERROR; `.failures` aliases `.violations`; empty feature is `.ok` | `exact` | `repo-local` |
| US-5: snapshot is injected | `uv run pytest tests/gherkin/ -k "sql or snapshot or injected"` | Same feature text over a literal snapshot and a SQL `load_snapshot` of that snapshot produces equal `FeatureReport.violations` | `exact` | `repo-local` |
| US-6: closed vocabulary + `register_step` | `uv run pytest tests/gherkin/ -k "register or catalog"` | Built-in phrase works with no extra Python; `register_step` adds a phrase that compiles to a `Rule`; `reset_steps` restores builtins so a later test does not see the extra phrase | `exact` | `repo-local` |
| US-7: unknown step / unmatched `When` | `uv run pytest tests/gherkin/ -k error` | Unknown `Then` and unmatched `When` raise `GherkinError` whose message contains the raw step text; `check` is not called | `exact` | `repo-local` |
| US-8: fake-backed suite, no live cadwork | `uv run pytest tests/gherkin/ tests/rules/test_library.py -k "ifc_type or material_is or count_is" -q` | Suite green under autouse `fake_cadwork` / literals; no skipif for cadwork | `exact` | `repo-local` |
| US-9: module doc + example tour | `uv run pytest tests/test_examples.py -k gherkin` | `examples.gherkin.run()` completes; `"gherkin"` is in `examples.MODULES`; `docs/gherkin.md` and `examples/features/framing.feature` exist | `exact` | `repo-local` |
| US-10: IFC through `cadwork.bim` | `uv run pytest tests/element/test_attributes.py tests/test_isolation.py tests/test_public_surface.py -k "ifc or GHERKIN or isolation"` | `beam.attrs.ifc_type = "IfcBeam"` reads back on the fake; unknown token raises `ValueError`; `pycadwork.gherkin` is absent from isolation offenders; `GHERKIN_EXPORTS` on `pycadwork` and in `__all__` | `exact` | `repo-local` |
| US-11: SQL / JSONL / fingerprint round-trip | `uv run pytest tests/persistence/ tests/versioning/ -k "ifc_type or attribute"` | Reader copies `ifc_type`; SQL round-trip preserves it; pre-column DB gains the column on `open_sqlite` and then round-trips `""`; `_attribute_fields` includes `ifc_type`; codec field-match still holds | `exact` | `repo-local` |

All rows are bot-runnable unattended (`uv run pytest …`). No graphical legs. No
deferred Manual: live cwapi3d `set_ifc_*` stringify is explicitly out of v1
(Spec Testing Decisions; architecture §5 runtime-verification gap).

## 3. Verification assets (Reuse vs `[NEW]`)

### 3.1 What was searched

| Repo | Searched (dir / keyword) | Found / Not found |
|------|--------------------------|-------------------|
| pycadwork | `tests/gherkin/` | not found — module does not exist yet |
| pycadwork | `examples/features/` | not found |
| pycadwork | `tests/conftest.py` autouse fake | `tests/conftest.py:11-39` |
| pycadwork | `FakeBimAdapter` / `_FakeElement` | `src/pycadwork/testing/cadwork_adapter.py:179-198, 1303-1339` |
| pycadwork | `tests/rules/test_engine.py`, `test_library.py` | selector + factory exact tests |
| pycadwork | `tests/element/test_attributes.py` | attrs round-trip on fake |
| pycadwork | `tests/persistence/test_schema.py` | `CREATE TABLE IF NOT EXISTS` reopen tests; **no** ADD COLUMN case |
| pycadwork | `tests/versioning/test_codec.py` field-match | `tests/versioning/test_codec.py:328-329` |
| pycadwork | `tests/test_examples.py`, `examples/MODULES` | `tests/test_examples.py:19-23`; `examples/__init__.py:61-80` |
| pycadwork | `tests/test_isolation.py`, `tests/test_public_surface.py` | isolation AST scan; `WORK_EXPORTS` pattern |
| pycadwork | goldens / `.feature` fixtures | not found |
| pycadwork | cadwork run-program IT for IFC | versioning IT only; none for BIM IFC |

### 3.2 Classification

| Asset | Kind | Verdict | Source / Rationale |
|-------|------|---------|--------------------|
| Autouse `fake_cadwork` | fixture/double | **Reuse** | `tests/conftest.py:11-39`; architecture §5 |
| `FakeCadworkAdapter` / `_FakeElement` | fixture/double | **Reuse** (extend with `ifc_type`) | architecture §5; research finding 3 |
| Snapshot record literals | fixture | **Reuse** (pattern) | `tests/rules/test_library.py:34-48` — Gherkin tests build the same way |
| `tests/rules/test_library.py` / `test_engine.py` | harness | **Reuse** (extend) | US-3 factories; US-6 selectors |
| `tests/element/test_attributes.py` | harness | **Reuse** (extend) | US-10 `attrs.ifc_type` round-trip |
| `tests/persistence/test_schema.py` | harness | **Reuse** (extend) | US-11 ADD COLUMN on a pre-column file |
| `tests/versioning/test_codec.py` | harness | **Reuse** | US-11 field-match; fails if record/schema drift |
| `tests/test_examples.py` | harness | **Reuse** | US-9; adding `"gherkin"` to `MODULES` is enough |
| `tests/test_isolation.py` | harness | **Reuse** | US-10; no change if gherkin stays above the seam |
| `tests/test_public_surface.py` export-tuple pattern | harness | **Reuse** (extend) | add `GHERKIN_EXPORTS` |
| `tests/gherkin/test_parser.py` | test module | **`[NEW]`** | Searched `tests/gherkin/`; missing because the product module is new. Producer of dialect / `GherkinError` (US-7) |
| `tests/gherkin/test_compile.py` | test module | **`[NEW]`** | Producer of US-1–3, zero-match ERROR, missing-geometry fail |
| `tests/gherkin/test_run.py` | test module | **`[NEW]`** | Producer of US-4, US-5 equality, US-6 `register_step` |
| `examples/features/framing.feature` | input | **`[NEW]`** | Searched `examples/features/`; missing. Success-demo file US-9 executes |
| `docs/gherkin.md` + `examples/gherkin.py` | teaching assets | **`[NEW]`** | Product docs/example; US-9 consumes them |
| `_FakeElement.ifc_type` | fixture field | **`[NEW]`** | Searched fake element fields; no IFC (research finding 3) |
| Golden `.feature` corpus / real `.3d` IFC IT | golden / e2e | **not authored** | Spec Testing Decisions: exact fake/literal asserts; no live IFC IT in v1 |

## 4. Verification tooling / harness (`[NEW]` only)

Every §2 method uses existing `uv run pytest`. No new comparator, runner, or
e2e command.

| Tool | What it does | Will live at | Becomes command | Consumed by |
|------|--------------|--------------|-----------------|-------------|
| *(none)* | — | — | — | — |

Existing commands used as-is:

- `uv run pytest tests/gherkin/`
- `uv run pytest tests/rules/test_library.py tests/rules/test_engine.py`
- `uv run pytest tests/element/test_attributes.py`
- `uv run pytest tests/persistence/ tests/versioning/`
- `uv run pytest tests/test_examples.py tests/test_isolation.py tests/test_public_surface.py`
- `uv run pytest -q` (full suite / no-regressions)

## 5. Whole-feature acceptance methodology (capstone contract)

### 5a. Per-repo capstone contract — one block per `Target repo`

- **Repo:** `pycadwork`
- **Broad command:** `uv run pytest tests/gherkin/ tests/rules/test_library.py tests/rules/test_engine.py tests/element/test_attributes.py tests/persistence/ tests/versioning/ tests/test_examples.py tests/test_public_surface.py tests/test_isolation.py -q`
- **Fed inputs:** in-memory snapshot literals, fake elements, `examples/features/framing.feature` (no external golden models)
- **Judged by:** §2 `exact` methods
- **Against goldens:** none
- **No-regressions clause:** full suite `uv run pytest -q` green
- **Graphical legs:** none — headless-only
- **Deferred Manual (HITL) legs:** none — fully AFK. (Live cwapi3d IFC stringify is out of v1, not deferred.)

### 5b. Cross-factory acceptance leg (integration capstone)

n/a — every story is repo-local; the per-repo capstone suffices.

## 6. Open questions

(none)

# Architecture: Gherkin live-model tests

> **Source Spec:** `docs/spec/gherkin-live-model-tests.md`
> **Source research:** `docs/research/gherkin-live-model-tests.md`
> **Status:** Draft
>
> Every decision below cites Spec §, research `file:line`, or is labeled `[NEW]` (rules in §10).

## 1. Context

This plan adds a Gherkin **driving adapter** over the existing snapshot linter
and one new snapshot fact (IFC 2x3 element type). Hexagonal shape is inherited:
`pycadwork.gherkin` never imports cwapi3d; it parses a `.feature` file, compiles
`Then` steps into `Rule` objects, and calls `rules.check`. IFC is sourced
through the existing `cadwork.bim` seam so `ModelReader` can put a canonical
string on `AttributeRecord`, which `SnapshotIndex` already exposes to rules.
The split exists so a plugin author can read the expected model in English
without a second evaluation engine, and so live-read and SQL-loaded snapshots
keep producing equal reports (research findings 1–2).

See Spec `## Solution` and research `## Context`.

## 2. System shape (hexagonal map)

```text
Driving adapters                         Domain core                         Driven adapters
────────────────                         ───────────                         ───────────────
plugin / script / examples
  .feature file  ──►  run_features  ──►  parser (stdlib subset)
                         │               compiler + step catalog
                         │                    │
                         │                    ▼
                         │               rules.check  ──►  SnapshotIndex(snapshot)
                         │                    │
                         └──────────►  FeatureReport ◄──── RuleReport (mapped)

Live Document / SQL / literals  ──►  ModelSnapshot
                                         ▲
ModelReader._attribute_record  ──►  attrs.ifc_type  ──►  cadwork.bim  ──►  BimAdapter
load_snapshot / gateways       ──►  attribute.ifc_type column                FakeBimAdapter
```

`pycadwork.gherkin` has **no cadwork driven port**. Its only collaborator is
`check(snapshot, rules)` plus the snapshot the caller already holds. IFC
plumbing is a parallel extension of the existing BIM seam so that snapshot
grows the fact Gherkin/rules assert.

### 2.1 Driving (primary) ports — what callers do

There is no separate Protocol. The **public surface is functions + frozen
DTOs** (package convention for `rules.check` / `cutting_list`; Spec
Implementation Decisions — Module and names).

| Port (conceptual) | Shape (key methods) | Source |
|-------------------|---------------------|--------|
| `run_features` | `run_features(snapshot, source) -> FeatureReport` | Spec Implementation Decisions — `run_features` and `FeatureReport` |
| `register_step` | `register_step(pattern, factory)`; process-global catalog | Spec — `register_step` |
| `FeatureReport` / `ScenarioResult` / `StepFailure` / `GherkinError` | frozen result / parse error | Spec — report DTOs |
| Rule factories | `ifc_type_is`, `material_is`, `count_is`, `all_of`, `named_equals` | Spec — Rules extensions |

### 2.2 Driven (secondary) ports — what the core needs from outside

| Port | Shape | Test double | Source |
|------|-------|-------------|--------|
| `rules.check` | existing `check(snapshot, rules, *, min_severity=) -> RuleReport` | none (pure); tests pass snapshot literals | research finding 1 (`rules/engine.py:134-201`) |
| `ModelSnapshot` / `SnapshotIndex` | existing records + `index.attribute` / `.geometry` | record literals | research `reporting/index.py:49-53` |
| `cadwork.bim` | existing + **`[NEW]`** `get_ifc_type` / `set_ifc_type` | `FakeBimAdapter` | Spec IFC plumbing; research finding 3 (`_bim.py:18-62`) |
| SQLite `attribute` table | existing + **`[NEW]`** `ifc_type` column and guarded `ADD COLUMN` | `open_sqlite(":memory:")` / tempfile | research finding 6 (`_connection.py:62-102`) |

No new driven-port Protocol. The seam stays the `cadwork` facade singleton.

### 2.3 Adapters

| Adapter | Implements port | Tech | Reuses |
|---------|-----------------|------|--------|
| `BimAdapter` | `cadwork.bim` | cwapi3d `bim_controller.get/set_ifc2x3_element_type` | existing class; **`[NEW]`** two methods, string in/out |
| `FakeBimAdapter` | same | in-memory `_FakeElement.ifc_type: str` | existing fake; **`[NEW]`** field + methods |
| `Attributes` | domain property | delegates to `cadwork.bim` | `attrs.color` pattern (`attributes.py:93-99`) |
| `ModelReader` / push mapper | snapshot ↔ live | reads/writes `attrs.ifc_type` | existing mappers; **`[NEW]`** one field |
| `AttributeGateway` | SQL | positional via `ATTRIBUTE` table | existing gateway; schema column drives it |
| stdlib parser | `.feature` text | no third-party Gherkin package | Spec Reach — zero new deps |

### 2.4 Cross-factory port contracts

n/a — no story spans repos.

## 3. Deep modules

### 3.1 `pycadwork.gherkin` (parser, catalog, compiler, runner)

- **Interface (what callers see):**
  - `run_features(snapshot, source: str | Path, *, min_severity=Severity.INFO) -> FeatureReport`
  - `register_step(pattern: str, factory) -> None`
  - `reset_steps() -> None` — restore the built-in catalog (test fixture;
    **`[NEW]`** named helper so sessions do not invent a private undo stack)
  - `GherkinError` on parse / unknown step / unmatched `When` (before `check`)
- **Hidden complexity:** dialect line parser; Scenario Outline expansion;
  Background prepend; `And`/`But` kind inheritance; path-vs-text `source`
  detection; closed Then phrases → `Rule`s with stable `rule_id`s
  (`feature:scenario:step-index` [+ outline row]); one `check` pass; map
  `Violation` → `StepFailure` by `rule_id`; dimension steps wrap
  `dimensions_within` so missing geometry **fails**; zero-match `every …`
  fails.
- **Why deep, not shallow:** the caller names a snapshot and a file; the
  module owns dialect, catalog, compile, and report mapping so plugin code
  never builds `ElementRule` literals for the closed vocabulary.
- **Source:** Spec Implementation Decisions — dialect, closed vocabulary,
  `run_features`; research findings 1, 8–9, 11.

`pycadwork.gherkin` **must not** import `cadwork`, `bim_controller`, or
`pycadwork.cadwork_adapter` (isolation test already forbids the first two).
It **may** import `pycadwork.rules` and `pycadwork.persistence.records`.
`pycadwork.rules` **must not** import `pycadwork.gherkin`.

### 3.2 Report DTOs (`pycadwork.gherkin`)

- **Interface:** frozen `StepFailure`, `ScenarioResult`, `FeatureReport`
  (`.ok`, `.failures` alias).
- **Hidden complexity:** none — values. Mapping from `RuleReport` lives in
  the runner, not on the DTO.
- **Why deep enough:** keep scenario/step identity next to the runner. Do
  not extend `RuleReport` with Gherkin fields (rules stay Gherkin-ignorant).
- **Source:** Spec `FeatureReport`; research finding 9 (`rules/records.py:59-67`
  as `.ok` semantics, not as the type to reuse).

### 3.3 Rule factories (`pycadwork.rules`)

- **Interface:** `ifc_type_is`, `material_is`, `count_is`, `all_of`,
  `named_equals` as documented in Spec Rules extensions. `check` /
  `ElementRule` / `ModelRule` / `dimensions_within` / `material_in` unchanged.
- **Hidden complexity:** `material_is` fails on empty (unlike `material_in`);
  `count_is` is a `ModelRule`; `all_of` AND-composes selectors; `ifc_type_is`
  reads `index.attribute(id).ifc_type`.
- **Why here, not inside gherkin:** Python lint scripts should assert IFC
  without a `.feature` file; the compiler is one client of the factories.
- **Source:** Spec Rules extensions; research finding 8.

### 3.4 IFC type plumbing (seam + snapshot + fingerprint)

- **Interface:**
  - `cadwork.bim.get_ifc_type(eid) -> str` /
    `set_ifc_type(eids, ifc_type: str) -> None`
  - `element.attrs.ifc_type` get/set
  - `AttributeRecord.ifc_type: str = ""` (appended)
  - canonical tokens `"IfcBeam"` etc. (v1 allow-list in Spec)
- **Hidden complexity:** stringify `bim_controller.get_ifc2x3_element_type`
  to canonical form; map token → `set_ifc_*` on the cwapi3d type object;
  `ValueError` on unknown set token; guarded `ALTER TABLE attribute ADD
  COLUMN ifc_type TEXT DEFAULT ''` in `init_schema`; append `record.ifc_type`
  to `_attribute_fields`; push mapper writes via `cadwork.bim`, not
  `cadwork.attributes`.
- **Why on `BimAdapter`, not `AttributesAdapter`:** cwapi3d places the calls
  on `bim_controller` (research finding 3). A third `IfcAdapter` would split
  the facade without a second controller. The domain still exposes
  `attrs.ifc_type` (color precedent).
- **Why on `AttributeRecord`, not a new table:** Gherkin/rules already look
  up `index.attribute`; a new satellite would add `SnapshotIndex` API, a
  codec `TABLE_SPECS` row, and a gateway for one string. Spec confirmation
  chose the column. Existing DBs need `ADD COLUMN` because
  `CREATE TABLE IF NOT EXISTS` will not migrate (research finding 6).
- **Source:** Spec IFC plumbing; research findings 3–7, 12. **`[NEW]`**
  methods/fields on existing types.

## 4. SOLID review (per module)

| Module | SRP — single reason to change | OCP — open for ext / closed for mod | LSP — contract for substitutes | ISP — port small per client | DIP — domain depends on ports only |
|--------|-------------------------------|-------------------------------------|--------------------------------|-----------------------------|-------------------------------------|
| `pycadwork.gherkin` | One reason: turn Gherkin + snapshot into a feature report | New phrases via `register_step`, not by editing `run_features` | Snapshot literals / live / SQL are interchangeable inputs | Callers see `run_features` + `register_step`; parser internals stay private | Depends on `rules.check` + records; never `bim_controller` |
| Report DTOs | One reason: describe a finished feature run | New fields additive on frozen types | Values, not substitutes | Read-only | No I/O |
| Rule factories | Each factory is one assertion kind | New checks are new factories; `check` stays closed | Selectors are callables; combinators substitute | Small free functions | Read `SnapshotIndex` only |
| IFC plumbing | One reason: round-trip IFC 2x3 type as a string | Allow-list is a table inside the adapter; new tokens are additive | Fake `get/set_ifc_type` matches live signatures | Two methods on `cadwork.bim`; one property on `attrs` | Domain uses facade; adapter is the I/O boundary |

## 5. Fake-first test strategy

- **Default policy:** Gherkin unit tests use **snapshot record literals** (no
  cadwork, no fake required). IFC adapter/domain tests use the autouse
  `FakeCadworkAdapter`. Persistence tests use `open_sqlite`. No mocks of
  `check` — the property under test is that compiled rules actually fail
  the snapshot. Mocks only if a test's property is "catalog dispatch
  called factory once" (not expected in v1).
- **Per-port doubles:** §2.2 — extend `FakeBimAdapter` / `_FakeElement` in
  `src/pycadwork/testing/cadwork_adapter.py` (shipped fake, not a tests-only
  fork).
- **Direct-tested deep modules:** parser, compiler, `run_features`
  (`tests/gherkin/`); new rule factories (`tests/rules/`); `attrs.ifc_type`
  (`tests/element/test_attributes.py`); schema ADD COLUMN
  (`tests/persistence/`); `_attribute_fields` (`tests/versioning/`).
- **Application-service-tested modules:** none.
- **Runtime verification of the real adapter:** v1 does **not** add a
  `/RUNPROGRAM` IFC IT (Spec Testing Decisions). The live methods are a
  stringify + `set_ifc_*` map; isolation tests plus cwapi3d docs (research
  References) cover the shape. Document that gap in `docs/gherkin.md`.
  Filling the allow-list from live method names is the research open
  question, done at implementation, not a new architecture decision.
- **Fake ownership:** continue `pycadwork.testing.cadwork_adapter`. Sessions
  must not roll a second fake. `reset_steps()` lives in `pycadwork.gherkin`
  so tests restore the catalog without copying internals.
- **Catalog isolation:** every `register_step` test calls `reset_steps` in
  a fixture teardown (Spec `register_step`).

## 6. Cross-cutting decisions

- **Concurrency / threading:** single-threaded, same as `rules.check`.
  `register_step` mutates a process-global catalog — not safe across
  threads; plugin authors and tests run sequentially inside cadwork / pytest.
- **Error handling:** exceptions for *authoring* mistakes (`GherkinError` ⊂
  `ValueError` for parse/unknown step/unmatched `When`; `ValueError` for
  unknown IFC set token). Assertion failures are **data** on
  `FeatureReport`, never raised — matching `RuleReport`. Empty feature is
  `ok=True`.
- **Logging / observability:** `FeatureReport` is the log. No logger.
- **Configuration / wiring:** `run_features` is a free function; it builds
  the parser/compiler internally. Snapshot is injected (caller owns
  `ModelReader` / SQL / literals). `cadwork` singleton is read at call
  time on the IFC property path so the test monkeypatch works.
- **ABI / packaging:** new public exports on `pycadwork`; **no extra
  dependency** (Spec Reach; research finding 11). Do not add `ifc_type` to
  `_BATCH_SETTERS` (Spec Out of Scope; research finding 12).
- **Schema evolution:** `init_schema` remains the single open-path. After
  `SCHEMA_SQL`, inspect `attribute` columns (PRAGMA table_info) and
  `ADD COLUMN` when `ifc_type` is missing. Idempotent with `CREATE TABLE
  IF NOT EXISTS` on fresh DBs.
- **Severity:** compiled Gherkin rules are `Severity.ERROR` so `.ok` is the
  test gate (research finding 9). Python callers of `ifc_type_is` may
  override `severity=`.

## 7. Out of scope (architectural)

- A `GherkinPort` Protocol over `run_features`
- Folding the parser into `pycadwork.rules`
- pytest-bdd / behave / official `gherkin` package
- pytest feature-file collector plugin
- Cadwork CLI / menu / dock runner
- Mutating `When` steps or `WorkUnit` integration
- `IfcAdapter` sub-facade
- Separate `ifc` snapshot table
- Changing `dimensions_within` skip-missing or `material_in` empty-pass
- `batch_apply` / `WorkUnit.apply` gaining `ifc_type`
- IFC4; tokens outside the v1 allow-list
- Non-English Gherkin keywords, tags, hooks, doc strings

## 8. Open questions

- Exact `cadwork.ifc_2x3_element_type.set_ifc_*` method names for the v1
  allow-list — confirm against cwapi3d at implementation (research Open
  questions). The adapter table is `[NEW]` until filled; the **shape**
  (canonical `str` in/out) is decided.

## 9. References

- Spec: `docs/spec/gherkin-live-model-tests.md`
- Research: `docs/research/gherkin-live-model-tests.md`
- Package architecture overview: `docs/architecture.md`
- Domain docs: `docs/rules.md`, `docs/testing.md`, `docs/persistence.md`
- cwapi3d IFC: <https://github.com/cwapi3d/cwapi3dpython/blob/main/docs/examples/bim_example.md>
- Cucumber Gherkin reference (dialect subset): <https://cucumber.io/docs/gherkin/reference/>

## 10. Reuse audit (REQUIRED — every capability classified)

### 10.1 What was searched

| Repo | Searched for | Found / Not found |
|------|--------------|-------------------|
| pycadwork | `gherkin`, `cucumber`, `behave`, `pytest-bdd`, `.feature` | not found |
| pycadwork | `ifc`, `IFC`, `ifc_type`, `get_ifc2x3_element_type` | not found (repo-wide) |
| pycadwork | `rules.check`, `ElementRule`, `ModelRule` | `src/pycadwork/rules/engine.py:67-201` |
| pycadwork | `dimensions_within`, `material_in`, `named` | `src/pycadwork/rules/library.py` |
| pycadwork | selectors `for_types` / `all_of` / `named_equals` | `for_types` etc. at `engine.py:100-123`; **no** `all_of` / `named_equals` |
| pycadwork | `RuleReport.ok` | `src/pycadwork/rules/records.py:59-67` |
| pycadwork | `SnapshotIndex` | `src/pycadwork/reporting/index.py:31-53` |
| pycadwork | `AttributeRecord` / `ATTRIBUTE` table | `persistence/records.py:73-93`, `schema.py:93-111` |
| pycadwork | `ModelReader._attribute_record` / `_apply_attributes` | `mappers.py:273-287`, `660-677` |
| pycadwork | `init_schema` / `CREATE TABLE IF NOT EXISTS` | `_connection.py:62-102`, `schema.py:10-13` |
| pycadwork | `BimAdapter` / `FakeBimAdapter` | `_bim.py:18-62`, `testing/cadwork_adapter.py:1303-1339` |
| pycadwork | `attrs.color` seam split | `element/components/attributes.py:93-99` |
| pycadwork | `_attribute_fields` fingerprint | `versioning/_sync.py:52-65` |
| pycadwork | `SnapshotCodec` / field-match test | `_codec.py:155-171`, `tests/versioning/test_codec.py:328-329` |
| pycadwork | `_BATCH_SETTERS` | `utility/_batch.py:10-18` — attributes seam only |
| pycadwork | example tour `MODULES` / public-surface | `examples/__init__.py:61-80`, `tests/test_public_surface.py` |
| pycadwork | isolation `bim_controller` | `tests/test_isolation.py:15-37` |
| pycadwork | runtime deps | `pyproject.toml:9-12` — `cwapi3d`, `rtree` |

### 10.2 Classification

| Capability | Verdict | Source / Rationale |
|------------|---------|--------------------|
| `rules.check` / `ElementRule` / `ModelRule` / `Selector` | **Reuse** | `rules/engine.py` — compilation target |
| `dimensions_within` | **Reuse** (wrap at compile) | `library.py:186-220` — Gherkin adds fail-on-missing-geometry without changing the built-in |
| `for_types` / `any_element` / `with_attribute` / `with_geometry` | **Reuse** | `engine.py:100-123` |
| `SnapshotIndex` | **Reuse** | `reporting/index.py` — `ifc_type` rides `attribute()` |
| `ModelSnapshot` / `ModelReader` / gateways | **Reuse** (extend records/schema) | persistence |
| `cadwork` facade / `BimAdapter` class | **Reuse** (extend) | `_bim.py` — add methods, do not add `IfcAdapter` |
| `FakeCadworkAdapter` / `_FakeElement` | **Reuse** (extend) | `testing/cadwork_adapter.py` — add `ifc_type` |
| `Attributes.color` pattern | **Reuse** (pattern) | `attributes.py:93-99` — `attrs.ifc_type` → `cadwork.bim` |
| `SnapshotCodec` / `TABLE_SPECS` | **Reuse** | follows schema+record field order |
| Example / docs / `__all__` wiring | **Reuse** (pattern) | `examples/__init__.py`, `test_public_surface.py` |
| `pycadwork.gherkin` (`run_features`, parser, compiler, catalog) | **`[NEW]`** | Searched gherkin/cucumber/behave/pytest-bdd/`.feature`; nothing. `rules` is a Python linter, not a parser (research finding 1). A third-party parser was rejected (Spec Reach). |
| `FeatureReport` / `ScenarioResult` / `StepFailure` / `GherkinError` | **`[NEW]`** | Searched `RuleReport`; that type has no scenario/step identity. Mapping keeps rules Gherkin-ignorant. |
| `register_step` / `reset_steps` / built-in catalog | **`[NEW]`** | No step registry in the package. `reset_steps` is the test-safe undo for a process-global catalog (Spec `register_step`). |
| `ifc_type_is` / `material_is` / `count_is` | **`[NEW]`** | Searched `library.py`; `material_in` empty-passes; no IFC; no count. Needed by both Gherkin and Python linters. |
| `all_of` / `named_equals` | **`[NEW]`** | Searched selectors; only `for_types` / `any_element` / `with_*`. Compiler needs AND + name match. |
| `BimAdapter.get_ifc_type` / `set_ifc_type` | **`[NEW]`** | Searched adapters and repo for `ifc`; empty. cwapi3d method lives on `bim_controller`, so extend `BimAdapter` rather than invent `IfcAdapter`. |
| `_FakeElement.ifc_type` + fake methods | **`[NEW]`** | Fake must mirror the new seam methods (docs/testing.md recipe). |
| `AttributeRecord.ifc_type` + `ATTRIBUTE` column | **`[NEW]`** | Record/schema have no IFC (research finding 4). Append-only to preserve positional gateways. |
| Guarded `ALTER TABLE … ADD COLUMN ifc_type` | **`[NEW]`** | Searched migrations; `init_schema` is `CREATE TABLE IF NOT EXISTS` only (research finding 6). Existing stores otherwise break on SELECT. |
| `_attribute_fields` includes `ifc_type` | **Reuse** (extend) | Manual tuple at `_sync.py:52-65` — omit and IFC-only edits are invisible to smart checkout (research finding 7) |
| `attrs.ifc_type` | **`[NEW]`** | Domain property; searched `Attributes` — no IFC. Follows color's split-seam pattern. |
| Canonical IFC string allow-list inside `BimAdapter` | **`[NEW]`** | cwapi3d uses a mutable type object, not a string (research Constraints). Domain/rules/gherkin must not import `ifc_2x3_element_type`. |

### 10.3 Reuse-first rule for downstream slicing

Seeds must not invent a second rule engine, a second snapshot index, a
pytest-bdd extra, an `IfcAdapter` sub-facade, or a separate `ifc` table.
Implement `run_features` on top of `rules.check`; add IFC as a string on
the existing BIM seam + `AttributeRecord`; wrap `dimensions_within` at
compile time rather than changing it; extend the shipped fake in place.
A slice that needs a capability not listed here must STOP and escalate,
not invent.

# Spec: Gherkin live-model tests

## Problem Statement

Plugin authors who want to accept a live cadwork 3D model (attributes,
dimensions, IFC types) today write Python: either `check(snapshot, [has_material(),
dimensions_within(...)])` or ad-hoc asserts on `Element.attrs`. That is
expressive but not the Gherkin/Cucumber form they want to share with the rest
of a project — a `.feature` file a reviewer can read without opening the
plugin. The existing rules engine already knows how to lint a `ModelSnapshot`;
it has no parser, and IFC type is not a fact the snapshot even carries.

## Solution

Add **`pycadwork.gherkin`**, a new public module that parses a documented
stdlib Gherkin subset, compiles each `Then` into one or more `Rule` objects,
and runs them through existing `rules.check`. The snapshot is injected by the
caller (`ModelReader().read()`, `load_snapshot(...)`, or a test literal), so
the same `.feature` file is valid against the open cadwork model and against
the fake in CI.

Extend **`pycadwork.rules`** with the factories the compiler needs
(`ifc_type_is`, a strict `material_is`, a count rule). Extend the BIM seam,
`attrs.ifc_type`, `AttributeRecord`, schema, mappers, fake, and versioning
fingerprint so IFC 2x3 type is a snapshot-backed string (`"IfcBeam"`).

```python
from pycadwork import ModelReader, run_features

report = run_features(ModelReader().read(), "features/framing.feature")
assert report.ok
for v in report.failures:
    print(v.scenario, v.step, v.element_id, v.message)
```

```gherkin
Feature: Framing QA

  Scenario: Studs are pine IfcBeams
    Given the model
    Then every beam named "Stud" has material "Pine"
    And every beam named "Stud" has ifc type "IfcBeam"
    And every beam named "Stud" has width 80
```

Gherkin `Then` compiles at `Severity.ERROR` so `report.ok` is the test gate.

## User Stories

1. **As a** plugin author, **I want** to write a `.feature` file that asserts
   element attributes on the current model, **so that** reviewers can read the
   expected names/materials/groups without opening Python.

2. **As a** plugin author, **I want** the same file to assert dimensions
   (exact or a range), **so that** section sizes are checked in the same
   scenario as names.

3. **As a** plugin author, **I want** to assert IFC 2x3 types (`IfcBeam`,
   `IfcWall`, …), **so that** BIM classification is part of model QA.

4. **As a** plugin author, **I want** `run_features(snapshot, path)` to return
   a structured report with `.ok` and per-step/element failures, **so that** I
   can assert in pytest or print the report inside cadwork without a Gherkin
   runner install.

5. **As a** plugin author, **I want** the snapshot to be injected, **so that**
   one feature file runs against a live `ModelReader().read()`, a pulled SQL
   store, or a test-literal snapshot.

6. **As a** plugin author, **I want** a closed Then vocabulary plus
   `register_step`, **so that** the common checks work with zero Python and I
   can still add a project-specific phrase that compiles to a `Rule`.

7. **As a** plugin author, **I want** unknown steps and illegal `When`
   mutations to fail with the step text, **so that** a typo does not silently
   skip.

8. **As a** test author of pycadwork, **I want** the suite to prove parser,
   compile, report, IFC round-trip, and the example feature against
   `FakeCadworkAdapter`, **so that** CI never needs a live cadwork process.

9. **As a** reader of the package, **I want** `docs/gherkin.md` and a runnable
   example on the CI tour, **so that** the module is taught the same way as
   rules and reporting.

10. **As a** maintainer, **I want** IFC get/set to go through `cadwork.bim`
    on the one seam (plain `str` in and out), **so that** isolation tests stay
    green and the fake can store the token.

11. **As a** user of persistence/versioning, **I want** `ifc_type` to
    round-trip through SQL and JSONL and to participate in content
    fingerprints, **so that** an IFC-only edit is not invisible to pull/push
    or smart checkout.

## Implementation Decisions

### Module and names

| Item | Decision |
|------|----------|
| Package | `src/pycadwork/gherkin/` |
| Public runner | `run_features(snapshot, source) -> FeatureReport` |
| `source` | `str` / `Path` to a `.feature` file, or the feature text itself (detected: if the string contains a newline or starts with `Feature:`, treat as text; else as a path) |
| Public types | `FeatureReport`, `ScenarioResult`, `StepFailure`, `GherkinError` |
| Step extension | `register_step(pattern: str, factory)` |
| Not named `check_gherkin` on `rules` | `rules` stays a pure linter; Gherkin is a driving adapter |
| Re-export | `from pycadwork import run_features, FeatureReport, register_step, ifc_type_is` (plus new rule factories) and `__all__` |
| No new runtime dependency | stdlib parser; `pyproject.toml` stays `cwapi3d` + `rtree` |

### Gherkin dialect (v1 subset)

Supported:

- `Feature:` title and optional description lines
- `Background:`
- `Scenario:` / `Scenario Outline:`
- `Given` / `When` / `Then` / `And` / `But` (keywords are case-sensitive as in
  Cucumber English)
- `Examples:` tables (header + rows) for Scenario Outline
- `#` comments to end of line
- Quoted strings `"..."` and bare numbers in steps

Rejected with `GherkinError` (message names the line):

- `language:` header, tags (`@wip`), doc strings (`"""`), `Rule:` blocks
- Any other keyword

`Given the model` / `Given the snapshot` is a no-op (the snapshot is the
`run_features` argument). Other `Given` phrases are unknown steps unless
registered.

`When` is parsed but **not** in the closed catalog. An unmatched `When`
raises `GherkinError` pointing at the step: v1 is read-only; do not compile
mutations. Plugin authors who want a `When` alias of `Then` can
`register_step`.

`And` / `But` inherit the previous step's kind (`Given`/`Then`).

Scenario Outline expansion happens before compile: each Examples row is one
`Scenario` with `<placeholders>` substituted.

### Closed Then vocabulary

Compiled at `Severity.ERROR`. `{type}` is a snapshot `element_type` token
(`beam`, `plate`, `wall`, …). `{axis}` is `length` / `width` / `height`.

| Phrase | Compiles to |
|--------|-------------|
| `every {type} named "{name}" has material "{material}"` | `material_is(material, selects=type+name)` |
| `every {type} named "{name}" has ifc type "{ifc}"` | `ifc_type_is(ifc, selects=type+name)` |
| `every {type} named "{name}" has {axis} {value}` | `dimensions_within` on that axis, range `(value, value)`, **absence of geometry fails** |
| `every {type} named "{name}" has {axis} between {lo} and {hi}` | `dimensions_within` inclusive, **absence of geometry fails** |
| `every {type} named "{name}" has group "{group}"` | element-rule on `attribute.group_name` |
| `every {type} named "{name}" has name "{name2}"` | not needed (selection already names them) — omit |
| `every element named "{name}" has …` | same factories with `any_element` + name (no type filter) |
| `there are {n} {type}s named "{name}"` | model-rule counting matches (`n` integer) |
| `there are {n} {type}s` | model-rule counting that type |

Unknown `Then` → `GherkinError` with the raw step text (unless registered).

A step that selects zero elements **fails** (ERROR): silent pass on a typo'd
name is worse than a false alarm. The count step is the way to assert
emptiness (`there are 0 beams named "Stud"`).

### `register_step`

```python
def register_step(pattern: str, factory: Callable[..., Rule | Sequence[Rule]]) -> None:
    """Register a Then/Given phrase.

    ``pattern`` is a full-match regex. Named groups are passed as kwargs to
    ``factory``. ``factory`` returns one ``Rule`` or a sequence. Registration
    is process-global; a test fixture should restore the catalog.
    """
```

Built-in phrases are registered the same way at import, so the extension
mechanism is the catalog, not a second path.

### `run_features` and `FeatureReport`

```python
def run_features(
    snapshot: ModelSnapshot,
    source: str | Path,
    *,
    min_severity: Severity = Severity.INFO,
) -> FeatureReport: ...

@dataclass(frozen=True, slots=True)
class StepFailure:
    scenario: str
    step: str
    rule_id: str
    element_id: int
    element_type: str
    message: str

@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: str
    ok: bool
    failures: tuple[StepFailure, ...]

@dataclass(frozen=True, slots=True)
class FeatureReport:
    title: str
    scenarios: tuple[ScenarioResult, ...]
    violations: tuple[StepFailure, ...]  # flattened, deterministic order
    rules_run: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """True when every scenario is ok (no ERROR-severity compiled failure)."""

    @property
    def failures(self) -> tuple[StepFailure, ...]:
        return self.violations
```

Implementation: compile all scenarios' steps to `Rule`s with stable `rule_id`s
that encode `feature:scenario:step-index` (and outline row index when
present). Call `check(snapshot, rules, min_severity=...)` **once**. Map
`Violation`s back onto scenarios via `rule_id`. Do not reimplement the
engine's sort; `FeatureReport.violations` is scenario order then the engine's
order within a scenario.

Empty feature (no scenarios) is `ok=True` with empty tuples.

Parse errors raise `GherkinError` (subclass of `ValueError`) **before**
`check` runs.

### Rules extensions

| Factory | Kind | Default severity | Notes |
|---------|------|------------------|-------|
| `ifc_type_is(expected: str, *, selects=, severity=)` | E | ERROR | empty IFC fails; compare canonical `"IfcBeam"` |
| `material_is(expected: str, *, selects=, severity=)` | E | ERROR | empty fails (unlike `material_in`) |
| `count_is(n: int, *, selects=, severity=)` | M | ERROR | count of selected elements equals `n` |
| `all_of(*selectors) -> Selector` | selector | — | AND-compose existing selectors |

`dimensions_within` stays as-is for Python callers (skip missing geometry).
The Gherkin compiler wraps it (or compiles an equivalent predicate) so
**missing geometry is a failure** for dimension steps. Do not change the
built-in's skip behaviour — that would silently alter existing lint scripts.

Add a selector helper used by the compiler (and public, because custom steps
will want it):

```python
def named_equals(name: str) -> Selector:
    """Select elements whose attribute.name equals ``name`` (missing attr fails the select)."""
```

`ifc_type_is` reads `index.attribute(id).ifc_type`. Missing attribute
satellite → fail `"no ifc type"`.

Re-export the new factories from `pycadwork.rules` and the top-level package.

### IFC type plumbing

Canonical form: `"Ifc"` + cwapi3d type token, matching the documented
`print(f'Ifc{ifc_type}')` — e.g. `"IfcBeam"`, `"IfcWall"`. Comparison is
exact and case-sensitive.

**Adapter** (`BimAdapter` + `FakeBimAdapter`):

```python
def get_ifc_type(self, eid: ElementId) -> str: ...
def set_ifc_type(self, eids: list[ElementId], ifc_type: str) -> None: ...
```

- Get: call `bim_controller.get_ifc2x3_element_type`, stringify to canonical
  form. Empty/unknown backend value → `""`.
- Set: map the canonical string onto the cwapi3d type object
  (`set_ifc_beam()` etc.) and call `set_ifc2x3_element_type`. Unknown token
  → `ValueError` listing the allow-list.
- v1 allow-list (extend only with evidence from cwapi3d): `IfcBeam`,
  `IfcColumn`, `IfcMember`, `IfcPlate`, `IfcWall`, `IfcSlab`, `IfcRoof`,
  `IfcOpeningElement`, `IfcBuildingElementProxy`.
- Fake stores a `str` on `_FakeElement.ifc_type` (default `""`).

**Domain:** `Attributes.ifc_type` property + setter, delegating to
`cadwork.bim` (same split as `color` → visualization). Not a method on
`BimAdapter` only — plugin authors already go through `element.attrs`.

**Snapshot:** append `ifc_type: str = ""` to `AttributeRecord` and
`ATTRIBUTE.columns` (same position). `ModelReader._attribute_record` reads
`element.attrs.ifc_type`. Push `_apply_attributes` calls
`cadwork.bim.set_ifc_type` when the record is present (including setting
`""` to clear).

**Existing SQLite:** after `SCHEMA_SQL` in `init_schema`, if table
`attribute` exists and has no `ifc_type` column, execute
`ALTER TABLE attribute ADD COLUMN ifc_type TEXT DEFAULT ''`. Idempotent;
new databases already have the column from `CREATE TABLE`.

**Versioning:** append `record.ifc_type` to `_attribute_fields` in
`versioning/_sync.py`. Codec follows schema/record automatically; the
field-match meta-test must stay green.

Do **not** add `ifc_type` to `batch_apply` / `_BATCH_SETTERS` in v1.

### Docs and examples

| File | Change |
|------|--------|
| `docs/gherkin.md` | Module README: dialect, closed phrases, `run_features`, `register_step`, IFC canonical strings, live vs fake |
| `docs/rules.md` | Row for `ifc_type_is`, `material_is`, `count_is`, `all_of`, `named_equals` |
| `docs/elements.md` | `attrs.ifc_type` |
| `docs/architecture.md` | Package-layout row + mermaid node for `gherkin` |
| `docs/README.md` | Bullet under “Working with the model” |
| `README.md` | Topic table row |
| `examples/gherkin.py` | Seed a small fake model, write/run a `.feature`, show pass and fail |
| `examples/features/framing.feature` | The success-demo feature (attributes, dimensions, IFC type) |
| `examples/__init__.py` | Append `"gherkin"` to `MODULES` |
| `examples/README.md` | Table row |
| `src/pycadwork/__init__.py` | Re-exports |

`docs/gherkin.md` **is** the module README. Do not add
`src/pycadwork/gherkin/README.md`.

### Public-surface test

Extend `tests/test_public_surface.py` with a `GHERKIN_EXPORTS` tuple:
`run_features`, `FeatureReport`, `ScenarioResult`, `StepFailure`,
`GherkinError`, `register_step`. New rule factories appear in the existing
rules export list.

## Testing Decisions

Fake-first; no live cadwork. New tests live under `tests/gherkin/`. IFC
adapter/domain/persistence tests extend the existing folders.

| Layer | What | How |
|-------|------|-----|
| Unit | Parser accepts the v1 dialect; rejects tags/doc-strings/`language:` with line-numbered `GherkinError` | `tests/gherkin/test_parser.py` |
| Unit | Scenario Outline expands rows; Background prepends steps | parser/compile tests |
| Unit | Closed Then phrases compile to rules that pass/fail snapshot literals | `tests/gherkin/test_compile.py` |
| Unit | Zero matches for `every …` is ERROR; `there are 0 …` is the empty assert | compile + `check` |
| Unit | Dimension step fails when geometry satellite is missing | unlike bare `dimensions_within` |
| Unit | `run_features` maps violations onto scenario/step; `.ok` false on any ERROR | `tests/gherkin/test_run.py` |
| Unit | Unknown step / illegal `When` raises `GherkinError` naming the text | |
| Unit | `register_step` adds a phrase; fixture restores the catalog | |
| Unit | `ifc_type_is` / `material_is` / `count_is` good and bad cases | `tests/rules/test_library.py` |
| Unit | `all_of` / `named_equals` selectors | `tests/rules/test_engine.py` |
| Adapter | `get_ifc_type` / `set_ifc_type` round-trip on the fake; unknown set token `ValueError` | `tests/cadwork_adapter/` or `tests/element/test_attributes.py` |
| Domain | `beam.attrs.ifc_type = "IfcBeam"` reads back | `tests/element/test_attributes.py` |
| Persistence | `ModelReader` copies `ifc_type`; SQL load/save round-trip; guarded ADD COLUMN on a pre-column DB | `tests/persistence/` |
| Versioning | `_attribute_fields` includes `ifc_type`; codec field-match still holds | `tests/versioning/` |
| Isolation | `pycadwork.gherkin` does not import `cadwork` / `bim_controller` | existing `test_isolation.py` |
| Public surface | Gherkin names re-exported and in `__all__` | `test_public_surface.py` |
| Examples | `examples.gherkin.run()` against the fake, including the `.feature` file | `MODULES` + `test_examples.py` |
| Invariant | Same feature over a live-read snapshot and a SQL-loaded snapshot → equal `FeatureReport.violations` | `tests/gherkin/` with fake + `open_sqlite` |

No real-cadwork integration test in v1: IFC stringify/`set_ifc_*` names are
confirmed against cwapi3d docs during implementation; the fake stores the
canonical string. A live `/RUNPROGRAM` probe is out of proportion to v1.

## Out of Scope

- pytest-bdd, behave, or the official `gherkin` PyPI parser
- pytest plugin that auto-collects `tests/**/*.feature`
- Cadwork terminal CLI / menu / dock to run features
- Mutating `When` steps, `WorkUnit` integration, geometry creation in
  scenarios
- Collision, connectivity, raycast, cover-discovery, storey-assignment
  phrases (authors may `register_step` them)
- German (or any non-English) Gherkin keywords
- Tags, hooks, doc strings, `Rule:` blocks, `language:` header
- IFC4 types; any token outside the v1 allow-list
- Adding `ifc_type` to `batch_apply` / `WorkUnit.apply`
- A separate `ifc` snapshot table
- Changing `dimensions_within` skip-missing-geometry behaviour for Python
  callers
- Changing `material_in` empty-pass behaviour
- Visual / golden-image model checks

## Further Notes

- Suggested plan slug: `gherkin-live-model-tests`.
- Keep `pycadwork.gherkin` above the seam; the only new cwapi3d calls are
  `bim_controller.get_ifc2x3_element_type` /
  `set_ifc2x3_element_type`.
- Document in `docs/gherkin.md`, in the first screenful, that this compiles
  to `pycadwork.rules` and does not replace it.
- Confirm `set_ifc_*` method names against cwapi3d when filling the adapter
  allow-list (research open question).

# Gherkin: live-model tests in English

`pycadwork.gherkin` compiles a documented Gherkin subset into
[`pycadwork.rules`](rules.md) and runs them through `check`. It does **not**
replace the rules engine: every `Then` becomes one or more `Rule` objects at
`Severity.ERROR`, and `report.ok` is the same ERROR-severity gate as
`RuleReport.ok`. Write Python `check(...)` when you already think in factories;
write a `.feature` file when a reviewer should read the expected model without
opening the plugin.

The snapshot is injected by the caller, so the same `.feature` file is valid
against the **live model** (`ModelReader().read()`), a **pulled SQL store**
(`load_snapshot(...)`), or a test-literal snapshot. The module never imports
cadwork.

```python
from pycadwork import run_features
from pycadwork.persistence import ModelReader

report = run_features(ModelReader().read(), "features/framing.feature")
assert report.ok
for v in report.failures:
    print(v.scenario, v.step, v.element_id, v.message)
```

v1 does **not** ship a live cadwork `/RUNPROGRAM` IFC integration test.
`attrs.ifc_type` get/set is proven on the shipped fake and against cwapi3d's
documented `set_ifc_*` names. Isolation tests stay green because Gherkin never
crosses the seam.

## Dialect (v1 subset)

Supported:

- `Feature:` title and optional description lines
- `Background:`
- `Scenario:` / `Scenario Outline:` with `Examples:` tables
- `Given` / `When` / `Then` / `And` / `But` (Cucumber English, case-sensitive)
- `#` comments to end of line
- Quoted strings `"..."` and bare numbers in steps

Rejected with `GherkinError` (the message names the line): `language:` headers,
tags (`@wip`), doc strings (`"""`), `Rule:` blocks, and any other keyword.

`Given the model` / `Given the snapshot` is a no-op — the snapshot is the
`run_features` argument. Other `Given` phrases are unknown unless registered.
`When` is parsed but not in the closed catalog; an unmatched `When` raises
`GherkinError` pointing at the step (v1 is read-only). `And` / `But` inherit
the previous step's kind. Scenario Outline rows expand before compile.

## Closed Then vocabulary

Compiled at `Severity.ERROR`. `{type}` is a snapshot `element_type` token
(`beam`, `plate`, `wall`, …). `{axis}` is `length` / `width` / `height`.

| Phrase | Compiles to |
|--------|-------------|
| `every {type} named "{name}" has material "{material}"` | `material_is` (empty fails) |
| `every {type} named "{name}" has ifc type "{ifc}"` | `ifc_type_is` |
| `every {type} named "{name}" has {axis} {value}` | `dimensions_within` on that axis; **missing geometry fails** |
| `every {type} named "{name}" has {axis} between {lo} and {hi}` | inclusive range; **missing geometry fails** |
| `every {type} named "{name}" has group "{group}"` | element-rule on `attribute.group_name` |
| `every element named "{name}" has …` | same factories, no type filter |
| `there are {n} {type}s named "{name}"` | `count_is` on type + name |
| `there are {n} {type}s` | `count_is` on that type |

A step that selects zero elements **fails**. Assert emptiness with a count
step (`there are 0 beams named "Stud"`). Unknown `Then` raises `GherkinError`
with the raw step text.

Python `dimensions_within` still skips missing geometry; only the Gherkin
compiler wraps it so a dimension step is an ERROR when the satellite is
absent. Do not change the built-in.

```gherkin
Feature: Framing QA

  Scenario: Studs are pine IfcBeams
    Given the model
    Then every beam named "Stud" has material "Pine"
    And every beam named "Stud" has ifc type "IfcBeam"
    And every beam named "Stud" has width 80
```

## `run_features` and the report

```python
report = run_features(snapshot, source, *, min_severity=Severity.INFO)
```

`source` is a path (`str` / `Path`) or the feature text itself: a string with a
newline or starting with `Feature:` is text; anything else is a path.

`FeatureReport` is frozen:

| Field | Meaning |
|-------|---------|
| `title` | the `Feature:` title |
| `scenarios` | one `ScenarioResult` per scenario (`name`, `ok`, `failures`) |
| `violations` | flattened `StepFailure`s, scenario order then engine order |
| `rules_run` | engine rule ids |
| `.ok` | `True` when every scenario is ok (no ERROR-severity failure) |
| `.failures` | alias for `violations` |

Each `StepFailure` carries `scenario`, `step`, `rule_id`, `element_id`,
`element_type`, and `message`. Parse errors raise `GherkinError` (a
`ValueError`) **before** `check` runs. An empty feature (no scenarios) is
`ok=True`.

## `register_step`

```python
from pycadwork import register_step, ElementRule, Severity

def factory(*, element_type: str, name: str) -> ElementRule:
    ...

register_step(
    r'every (?P<element_type>\w+) named "(?P<name>[^"]*)" is tagged',
    factory,
)
```

`pattern` is a full-match regex. Named groups are kwargs to `factory`, which
returns one `Rule` or a sequence. Registration is process-global; tests call
`reset_steps()` to restore the built-in catalog. Built-in phrases are
registered the same way at import.

## IFC type

Canonical form is `"Ifc"` plus the cwapi3d type token, compared exactly and
case-sensitively: `"IfcBeam"`, `"IfcWall"`, `"IfcColumn"`, `"IfcMember"`,
`"IfcPlate"`, `"IfcSlab"`, `"IfcRoof"`, `"IfcOpeningElement"`,
`"IfcBuildingElementProxy"`. Empty or unknown backend values become `""`.
Setting an unknown token raises `ValueError` listing that allow-list.

Plugin authors read and write `element.attrs.ifc_type` (it delegates to
`cadwork.bim`, the same split as `color` → visualization). The snapshot field
is `AttributeRecord.ifc_type`, so a Gherkin `has ifc type "IfcBeam"` and a
Python `ifc_type_is("IfcBeam")` see the same string.

## Live vs fake

`run_features` never opens cadwork. You pass the snapshot:

- **Live:** `run_features(ModelReader().read(), path)` inside cadwork
- **SQL:** `run_features(load_snapshot(connection, guid), path)` after a pull
- **CI / tests:** seed elements through the public API under the autouse fake
  (`tests/conftest.py`) and call `run_features(ModelReader().read(), path)`
  the same way — `examples/gherkin.py` is that tour

The live BIM adapter's stringify of `bim_controller.get_ifc2x3_element_type`
is **not** exercised by a `/RUNPROGRAM` test in v1 (architecture §5). The fake
stores the canonical token; isolation tests forbid Gherkin from importing
`bim_controller`.

A runnable tour — seed a small model, run
[`examples/features/framing.feature`](../examples/features/framing.feature),
show a pass and a fail — lives in [`examples/gherkin.py`](../examples/gherkin.py).

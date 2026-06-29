# Rules: a linter for the model

`pycadwork.rules` validates a model against declarative rules and returns a
structured pass/fail/severity report. It is the sibling of
[`reporting`](reporting.md): pure functions over the same
`ModelSnapshot`, so the *same* rules run against the **live model**
(`ModelReader().read()`) or a **pulled SQL store** (`load_snapshot(connection,
guid)`) — and the module never touches cadwork or SQL, so it is unit-testable
from record literals.

```python
from pycadwork import check, has_material, assigned_to_storey, dimensions_within
from pycadwork.persistence import ModelReader

rules = [has_material(), assigned_to_storey(), dimensions_within(width=(40, 300))]

report = check(ModelReader().read(), rules)
print(report.ok)            # False if any ERROR-severity rule failed
for v in report.failures:
    print(v.severity.name, v.rule_id, v.element_id, v.message)
```

`check` builds the shared `SnapshotIndex` once, runs every rule in one pass, and
returns a `RuleReport` whose `violations` are deterministically sorted
(`severity` desc, then `rule_id`, `element_id`, `message`).

## Two rule shapes

Rules come in two shapes, because forcing both through one signature would force
a path the package avoids:

- **`ElementRule`** — evaluated independently per *selected* element. Its
  predicate returns `None` to pass or a `str` detail to fail. This is the common
  case (every beam has a material, names are non-empty, dimensions are in range).
- **`ModelRule`** — evaluated once over the whole snapshot, yielding its own
  findings. This is for genuinely cross-element checks (no two parts share a
  production number but differ in size) that a per-element predicate can't
  express.

`check` takes a mixed list of both and unifies their output into one report.

## Built-in rules

Each built-in is a factory free function (like reporting's `by_*` axes).
Element rules accept a `selects=` scope override and a `severity=` override;
model rules accept `severity=`. Element-level (**E**) unless marked **M**:

| Rule | Kind | Default severity | Checks |
|------|------|------------------|--------|
| `has_material()` | E | WARNING | `material_name` is non-empty |
| `named()` | E | WARNING | `name` is non-empty |
| `has_production_number()` | E | INFO | `production_number > 0` |
| `assigned_to_storey()` | E | WARNING | the element has a storey assignment |
| `material_in(allowed)` | E | ERROR | material is in the allowed set (empty passes) |
| `naming_matches(pattern, field="name")` | E | WARNING | `name`/`group_name`/`subgroup` fully matches a regex |
| `dimensions_within(length=…, width=…, height=…)` | E | ERROR | the given axes are within range (beams/plates) |
| `volume_between(min, max)` | E | WARNING | volume in range |
| `weight_between(min, max)` | E | INFO | weight in range |
| `material_is_known()` | M | ERROR | the material has a catalog master row |
| `no_duplicate_part_numbers_with_different_dims()` | M | ERROR | one part number denotes one size |
| `unique_assembly_numbers()` | M | WARNING | one assembly number is homogeneous (name/material) |
| `every_member_has_container_parent()` | M | INFO | a container-parent reference is confirmed by a member link |

By design there is **no** built-in "minimum spacing between drillings": the
snapshot carries only an AABB and three axis points per element, not the
drilling geometry an honest spacing test needs. Write that as a custom
`ModelRule` over the geometry you trust.

## A custom rule

A custom rule is one dataclass literal — no factory required:

```python
from pycadwork import ElementRule, Severity, check, for_types

def too_heavy(index, element):
    g = index.geometry(element.id)
    if g is None or g.weight <= 50.0:
        return None
    return f"{g.weight:.0f} kg exceeds the hand-lift limit"

rule = ElementRule(
    id="hand-lift-limit",
    description="part must be liftable by hand",
    severity=Severity.WARNING,
    selects=for_types("beam", "plate"),
    check=too_heavy,
)

report = check(ModelReader().read(), [rule])
```

Selectors (`for_types(...)`, `any_element()`, `with_attribute()`,
`with_geometry()`) decide which elements a rule sees; the predicate receives the
shared `SnapshotIndex` and the element's record.

## Severity and the CI gate

`Severity` is `INFO < WARNING < ERROR`. `report.ok` is `True` when there are **no
ERROR violations** — `WARNING`/`INFO` advisories surface in the report without
breaking the gate, so `assert check(snapshot, rules).ok` is a clean check.
`check(..., min_severity=Severity.WARNING)` drops everything below the cut.

## CSV

The stream-based stdlib-csv writer takes the report and a text stream (the
caller owns the file):

```python
import io
from pycadwork import write_violations_csv

stream = io.StringIO()
write_violations_csv(report, stream)   # rule_id, severity, element_id, element_type, message
```

A runnable tour — built-in rules, a model-level rule, a custom rule, the
live==SQL equivalence, and the CSV writer — lives in
[`examples/rules.py`](../examples/rules.py).

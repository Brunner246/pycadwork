# Research: gherkin-live-model-tests

## Context

Plugin authors already have a Python linter for models: `pycadwork.rules.check`
runs `ElementRule` / `ModelRule` factories over a `ModelSnapshot` and returns a
sorted `RuleReport` whose `.ok` is the CI gate (no `ERROR` violations). The
same pass works on a live read (`ModelReader().read()`) or a pulled SQL store
(`load_snapshot`). There is no Gherkin parser, no `.feature` runner, and no
IFC type anywhere in the package — a repo-wide search for `ifc` is empty.

This plan adds a Gherkin driving layer that compiles scenarios into the existing
rule engine, and it adds IFC 2x3 element type as a snapshot-backed fact so
those scenarios can assert it.

## Scope of exploration

- `src/pycadwork/rules/` (`engine.py`, `library.py`, `records.py`, `__init__.py`)
- `docs/rules.md`, `examples/rules.py`, `tests/rules/`
- `src/pycadwork/persistence/records.py`, `schema.py`, `mappers.py`, `gateways.py`, `_connection.py`
- `src/pycadwork/reporting/index.py` (`SnapshotIndex`)
- `src/pycadwork/cadwork_adapter/_bim.py`, `_attributes.py`, `_facade.py`
- `src/pycadwork/element/components/attributes.py`
- `src/pycadwork/testing/cadwork_adapter.py` (`_FakeElement`, `FakeBimAdapter`)
- `src/pycadwork/versioning/_codec.py`, `_sync.py`
- `src/pycadwork/utility/_batch.py`
- `src/pycadwork/__init__.py`, `docs/architecture.md`, `docs/testing.md`
- `examples/__init__.py`, `tests/test_examples.py`, `tests/test_public_surface.py`, `tests/test_isolation.py`
- `pyproject.toml` (runtime deps, extras)
- cwapi3d `bim_controller` IFC 2x3 surface (public docs)

## Key findings

1. **`rules` is already the evaluation engine, and it is not Gherkin.**
   `check` (`rules/engine.py:134-201`) builds one `SnapshotIndex`, runs mixed
   `ElementRule` / `ModelRule` lists, and returns a deterministically sorted
   `RuleReport`. Built-ins (`has_material`, `dimensions_within`, `named`, …)
   are Python factory functions (`rules/library.py`). A custom rule is a
   dataclass literal (`docs/rules.md:69-91`). Nothing in this package parses
   Feature/Scenario text.

2. **The engine is snapshot-pure — that is the property to keep.**
   The module docstring (`rules/engine.py:22-26`) and `docs/rules.md:1-9`
   state the contract: no cadwork import, no SQL; live and SQL sources must
   yield equal reports. A Gherkin runner that called `element.attrs` live
   would break that equality and skip the fake-first suite.

3. **IFC type is a cwapi3d BIM call, not an attribute-controller field.**
   Public cwapi3d examples use `bim_controller.get_ifc2x3_element_type(eid)` /
   `set_ifc2x3_element_type([eid], ifc_type)` on a `cadwork.ifc_2x3_element_type`
   object (`set_ifc_wall()`, `is_ifc_member(...)`). Printing is
   `f'Ifc{ifc_type}'` (e.g. `IfcWall`). `BimAdapter`
   (`cadwork_adapter/_bim.py:18-62`) today only wraps building/storey
   assignment and elevations. `FakeBimAdapter`
   (`testing/cadwork_adapter.py:1303-1339`) mirrors that and has no IFC field
   on `_FakeElement` (`testing/cadwork_adapter.py:179-198`).

4. **The snapshot cannot assert IFC today.**
   `AttributeRecord` (`persistence/records.py:73-93`) ends at
   `assembly_number`. `ModelReader._attribute_record`
   (`persistence/mappers.py:273-287`) copies `attrs.name` … `assembly_number`.
   Push (`mappers.py:660-677`) writes those same fields through
   `cadwork.attributes` and never talks to `cadwork.bim`.
   `SnapshotIndex.attribute` (`reporting/index.py:49-50`) is the lookup rules
   already use.

5. **`attrs.color` is the precedent for a property whose seam is not
   `cadwork.attributes`.**
   `Attributes.color` (`element/components/attributes.py:93-99`) delegates to
   `cadwork.visualization`. IFC can live on `attrs.ifc_type` and delegate to
   `cadwork.bim` the same way. Color is *not* on `AttributeRecord` (it is
   visualization, not a rules fact). IFC *must* be on the snapshot because
   rules/Gherkin are snapshot-pure.

6. **Schema apply is `CREATE TABLE IF NOT EXISTS` only — a new column on
   `attribute` will not appear on existing SQLite files.**
   `open_sqlite` (`persistence/_connection.py:91-102`) runs `SCHEMA_SQL` on
   every open; `init_schema` (`_connection.py:62-64`) is that script.
   `ATTRIBUTE` (`persistence/schema.py:93-111`) has no `ifc_type`. Adding a
   column to the `Table` literal updates *new* databases and the positional
   gateway mapping (`gateways.py:71-75`: record fields ↔ column names in
   order). Existing files keep the old table. A guarded
   `ALTER TABLE attribute ADD COLUMN ifc_type TEXT DEFAULT ''` on open is
   required, or existing stores will raise on SELECT/INSERT of the new field.

7. **Versioning fingerprints enumerate attribute fields by hand.**
   `SnapshotCodec` binds `ATTRIBUTE` → `AttributeRecord` → `attributes`
   (`versioning/_codec.py:158-161`). A meta-test
   (`tests/versioning/test_codec.py:328-329`) asserts dataclass field names
   equal table column names, so a schema/record pair that stays in lockstep
   is enough for JSONL. `_attribute_fields` in `versioning/_sync.py:52-65`
   is a **manual** tuple (`name` … `assembly_number`) used for smart-switch
   content fingerprints — omit `ifc_type` there and an IFC-only edit is
   invisible to checkout reconciliation.

8. **`dimensions_within` and `material_in` are close, not identical, to
   Gherkin assertions.**
   `dimensions_within` (`rules/library.py:186-220`) checks inclusive ranges
   on beams/plates and **skips** missing geometry (no false fail).
   `material_in` (`library.py:128-150`) lets empty material **pass**. A
   Gherkin `Then … has material "Pine"` must fail on empty; a
   `Then … has width 80` can reuse `dimensions_within(width=(80, 80))`.
   There is no `ifc_type_is`, no count rule, and no selector combinator
   (`all_of`) — `for_types` / `any_element` / `with_attribute` /
   `with_geometry` are the only selectors (`engine.py:100-123`).

9. **`RuleReport.ok` ignores WARNING/INFO** (`rules/records.py:59-67`).
   Built-in lint defaults are often WARNING (`has_material`, `named`).
   Compiled Gherkin `Then` steps must use `Severity.ERROR` or
   `assert report.ok` will stay green on failed scenarios.

10. **The public-surface and example-tour patterns are mechanical.**
    New modules re-export from `pycadwork/__init__.py` (rules:
    `__init__.py:131-157`), list names in `__all__`, add a
    `*_EXPORTS` tuple in `tests/test_public_surface.py` (work:
    `test_public_surface.py:67-79`), add `docs/<module>.md`, append to
    `examples/MODULES` (`examples/__init__.py:61-80`), and ride
    `tests/test_examples.py`. Isolation (`tests/test_isolation.py:15-37`)
    forbids `bim_controller` outside `cadwork_adapter`.

11. **Runtime dependency bar is two packages.**
    `pyproject.toml:9-12` — `cwapi3d`, `rtree`. `testing` extra is empty.
    pytest is a *dev* group, not a runtime extra. Cadwork's embedded
    Python will not have pytest-bdd/behave unless the plugin author
    installs them. A stdlib Gherkin subset keeps the runner callable from
    a cadwork script as `run_features(ModelReader().read(), path)`.

12. **`batch_apply` does not know IFC and should not gain it in this plan.**
    `_BATCH_SETTERS` (`utility/_batch.py:10-18`) maps a closed set onto
    `cadwork.attributes` setters only. IFC writes go through `cadwork.bim`.
    Extending `batch_apply` / `WorkUnit.apply` would mix seams and is
    unnecessary for read-only Gherkin.

## Reusable building blocks

| Block | Path | Why it is reusable |
|-------|------|--------------------|
| `check` / `ElementRule` / `ModelRule` / `Selector` | `src/pycadwork/rules/engine.py:67-201` | Compilation target; do not reimplement evaluation |
| `RuleReport.ok` / `Violation` | `src/pycadwork/rules/records.py:22-67` | Gate and per-element failure shape |
| `for_types`, `any_element`, `with_attribute`, `with_geometry` | `src/pycadwork/rules/engine.py:100-123` | Selector primitives the compiler composes |
| `dimensions_within` | `src/pycadwork/rules/library.py:186-220` | Range and exact-width `Then` steps |
| `SnapshotIndex.attribute` / `.geometry` | `src/pycadwork/reporting/index.py:49-53` | O(1) fact lookup inside compiled predicates |
| `ModelReader.read` / `_attribute_record` | `src/pycadwork/persistence/mappers.py:170-287` | Live → snapshot; add `ifc_type` here |
| `ModelReader._apply_attributes` | `src/pycadwork/persistence/mappers.py:660-677` | Snapshot → live push; IFC must go through `cadwork.bim` |
| `ATTRIBUTE` table + `AttributeRecord` | `src/pycadwork/persistence/schema.py:93-111`, `records.py:73-93` | Add `ifc_type` in matching field/column order |
| `TableDataGateway._to_row` / `_from_row` | `src/pycadwork/persistence/gateways.py:71-75` | Positional; follows schema automatically |
| `BimAdapter` / `FakeBimAdapter` | `cadwork_adapter/_bim.py:18-62`, `testing/cadwork_adapter.py:1303-1339` | New get/set IFC pair + fake field |
| `Attributes.color` seam split | `element/components/attributes.py:93-99` | Pattern for `attrs.ifc_type` → `cadwork.bim` |
| `SnapshotCodec` + field-match test | `versioning/_codec.py:155-171`, `tests/versioning/test_codec.py:328-329` | JSONL picks up a new attribute column if record+schema match |
| `_attribute_fields` | `versioning/_sync.py:52-65` | **Must** list `ifc_type` or fingerprints ignore it |
| Example tour / public-surface / isolation | `examples/__init__.py:61-80`, `tests/test_public_surface.py`, `tests/test_isolation.py` | Mechanical packaging of a new module |
| `FakeCadworkAdapter` autouse fixture | `tests/conftest.py:11-39` | Suite never needs a live cadwork process |

## Constraints & gotchas

- **Version isolation.** `tests/test_isolation.py` fails if `bim_controller`
  is imported outside `cadwork_adapter`. The Gherkin module and `rules` must
  not import cwapi3d types (`ifc_2x3_element_type`). The adapter returns and
  accepts a plain `str` (`"IfcBeam"`).
- **Existing SQLite files.** `CREATE TABLE IF NOT EXISTS` will not add
  `ifc_type`. Guarded `ALTER TABLE … ADD COLUMN` on open, or SELECT after
  an upgrade raises `OperationalError: no such column: ifc_type`.
- **Record/schema field order.** Gateways and the codec serialize
  positionally. `ifc_type` must be appended (not inserted) on both
  `AttributeRecord` and `ATTRIBUTE.columns`.
- **`material_in` empty-pass.** Do not compile `has material "Pine"` to
  `material_in({"Pine"})` — empty would pass. Need a strict factory
  (`material_is`) or an inline `ElementRule`.
- **Missing geometry is silent in `dimensions_within`.** A `Then … has
  width 80` on an element with no geometry satellite currently passes.
  Decide in the Spec whether Gherkin treats absence as fail (recommended
  for a test) by wrapping the built-in or compiling a stricter predicate.
- **IFC setter API is object-mutating, not a string.** cwapi3d uses
  `ifc_type.set_ifc_wall(); bc.set_ifc2x3_element_type([id], ifc_type)`.
  The adapter must own the string ↔ object map. Unknown tokens →
  `ValueError`. Exact `set_ifc_*` names for the v1 allow-list need a
  live or docs check at implementation time.
- **Float equality.** `has width 80` → `dimensions_within(width=(80, 80))`
  is a closed interval, not `math.isclose`. Authors who need slack write
  `between`.
- **pytest is not available inside cadwork by default.** The success demo
  is `run_features(snapshot, path).ok`, not pytest-bdd collection.

## Open questions

- Exact `cadwork.ifc_2x3_element_type.set_ifc_*` method names for the v1
  allow-list (IfcBeam, IfcColumn, IfcMember, IfcPlate, IfcWall, IfcSlab,
  IfcRoof, IfcOpeningElement, IfcBuildingElementProxy) — confirm against
  cwapi3d at implementation; the adapter table is `[NEW]` until then.
- Whether cwapi3d also exposes IFC4 types in the versions pycadwork
  supports — deferred; v1 is IFC 2x3 strings only.

## Out of scope

- pytest-bdd / behave / official `gherkin` package
- Cadwork CLI or menu to launch features
- Mutating `When` steps (create/edit geometry, `WorkUnit`)
- Collision, connectivity, raycast, or cover-discovery steps
- German Gherkin keywords (`language: de`)
- Gherkin tags, doc strings, hooks, and `language:` header
- Adding `ifc_type` to `batch_apply` / `WorkUnit.apply`
- Putting IFC on a separate snapshot table

## References

- `docs/rules.md` — current linter contract
- `docs/testing.md` — fake-first seam
- `docs/architecture.md:68-69` — `rules` as snapshot-pure domain module
- `docs/design-principles.md:4-6` — version isolation
- cwapi3d IFC examples: <https://github.com/cwapi3d/cwapi3dpython/blob/main/docs/examples/bim_example.md>
- cwapi3d `ifc_2x3_element_type` module: <https://github.com/cwapi3d/cwapi3dpython/blob/main/docs/documentation/ifc_2x3_element_type.md>
- Cucumber Gherkin reference (dialect subset only): <https://cucumber.io/docs/gherkin/reference/>

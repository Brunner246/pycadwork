# Seed: IFC type on snapshot + rule factories

> Pull this card to start a new session. Prefer opening the session in the **Target repo**.

## Kanban metadata

- **Card ID:** 01
- **Type:** AFK
- **Headless:** true
- **Capstone:** false
- **Producer:** false
- **Interim:** false
- **Integration:** false
- **Lane:** L1
- **Blocked by:** None — Ready
- **Estimated size:** L
- **Priority:** Highest
- **Target repo:** `pycadwork`
- **Branch:** `feature/gherkin-live-model-tests-01-ifc-snapshot`

## Source documents

- **Spec:** `docs/spec/gherkin-live-model-tests.md`
- **Research:** `docs/research/gherkin-live-model-tests.md`
- **Architecture:** `docs/architecture/gherkin-live-model-tests.md`
- **Verification:** `docs/verification/gherkin-live-model-tests.md`

## Scope (Definition of Ready)

Make IFC 2x3 element type a snapshot-backed string and add the rule factories
Gherkin will compile to. Extend `BimAdapter` + shipped fake with
`get_ifc_type` / `set_ifc_type` (canonical `"IfcBeam"`). Expose
`attrs.ifc_type`. Append `ifc_type` on `AttributeRecord` and `ATTRIBUTE`,
guarded `ADD COLUMN` in `init_schema`, mapper read/push, `_attribute_fields`.
Add `ifc_type_is`, `material_is`, `count_is`, `all_of`, `named_equals`.
Re-export the new factories. Fake-backed tests for US-3 (factory), US-10,
US-11.

Do not parse Gherkin in this seed.

## Spec guardrail

**In scope (verbatim):**

> Canonical form `"IfcBeam"`. `cadwork.bim.get_ifc_type` / `set_ifc_type`; unknown set token `ValueError` listing the v1 allow-list (`IfcBeam`, `IfcColumn`, `IfcMember`, `IfcPlate`, `IfcWall`, `IfcSlab`, `IfcRoof`, `IfcOpeningElement`, `IfcBuildingElementProxy`). `Attributes.ifc_type` delegates to `cadwork.bim`. Append `ifc_type: str = ""` on `AttributeRecord` and `ATTRIBUTE.columns`. `ModelReader._attribute_record` reads `element.attrs.ifc_type`; push calls `cadwork.bim.set_ifc_type`. After `SCHEMA_SQL`, if `attribute` has no `ifc_type` column, `ALTER TABLE attribute ADD COLUMN ifc_type TEXT DEFAULT ''`. Append `record.ifc_type` to `_attribute_fields`. Factories: `ifc_type_is`, `material_is` (empty fails), `count_is`, `all_of`, `named_equals`. Re-export from `pycadwork.rules` and the top-level package. Do not add `ifc_type` to `batch_apply`.

**Out of scope (verbatim):**

> Gherkin parser / `run_features` / `register_step` / `.feature` files. pytest-bdd. Cadwork CLI. Mutating `When`. `IfcAdapter` sub-facade. Separate `ifc` table. Changing `dimensions_within` skip-missing or `material_in` empty-pass. `batch_apply` / `WorkUnit.apply` gaining `ifc_type`. IFC4. Module README and examples (seed 03). Confirm `set_ifc_*` names against cwapi3d docs when filling the adapter allow-list.

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** rule factories (`ifc_type_is`, `material_is`, `count_is`, `all_of`, `named_equals`); `attrs.ifc_type`
- **Driven port(s) + test double:** `cadwork.bim` via existing `FakeCadworkAdapter`; **`[NEW]`** `get_ifc_type` / `set_ifc_type` + `_FakeElement.ifc_type`
- **Deep module(s):** IFC plumbing (architecture §3.4); rule factories (architecture §3.3)
- **SOLID / cross-cutting (verbatim):** Domain/rules must not import `ifc_2x3_element_type` — adapter returns/accepts `str`. `init_schema` remains the single open-path; PRAGMA table_info then `ADD COLUMN` when missing. Push mapper writes IFC via `cadwork.bim`, not `cadwork.attributes`. Append-only on record/schema to preserve positional gateways.
- **Out of scope (architecture §7):** `GherkinPort`; folding parser into rules; pytest-bdd; CLI; mutating `When`; `IfcAdapter`; separate `ifc` table; changing `dimensions_within` / `material_in`; `batch_apply` IFC; IFC4; non-English Gherkin

If this slice needs a `[NEW]` architectural decision, STOP and run `/lp-to-architecture` first.

## Reusable building blocks

- `src/pycadwork/cadwork_adapter/_bim.py` — add IFC methods here
- `src/pycadwork/testing/cadwork_adapter.py` — `_FakeElement` + `FakeBimAdapter`
- `src/pycadwork/element/components/attributes.py` — `color` seam-split pattern for `ifc_type`
- `src/pycadwork/persistence/records.py` / `schema.py` / `mappers.py` / `_connection.py`
- `src/pycadwork/persistence/gateways.py` — positional; follows schema
- `src/pycadwork/versioning/_sync.py` — `_attribute_fields`
- `src/pycadwork/rules/engine.py` — selectors; add `all_of` / `named_equals`
- `src/pycadwork/rules/library.py` — factory pattern
- `tests/rules/test_library.py` / `test_engine.py`
- `tests/element/test_attributes.py`
- `tests/persistence/test_schema.py`
- `tests/versioning/test_codec.py` field-match
- `tests/conftest.py` — autouse fake
- cwapi3d IFC examples (research References) — `set_ifc_*` names

## Touched files (predicted)

```
- src/pycadwork/cadwork_adapter/_bim.py — get_ifc_type / set_ifc_type
- src/pycadwork/testing/cadwork_adapter.py — _FakeElement.ifc_type + fake methods
- src/pycadwork/element/components/attributes.py — attrs.ifc_type
- src/pycadwork/persistence/records.py — AttributeRecord.ifc_type
- src/pycadwork/persistence/schema.py — ATTRIBUTE ifc_type column
- src/pycadwork/persistence/_connection.py — guarded ADD COLUMN
- src/pycadwork/persistence/mappers.py — read + push
- src/pycadwork/versioning/_sync.py — _attribute_fields
- src/pycadwork/rules/engine.py — all_of, named_equals
- src/pycadwork/rules/library.py — ifc_type_is, material_is, count_is
- src/pycadwork/rules/__init__.py — re-exports
- src/pycadwork/__init__.py — re-export new factories
- tests/element/test_attributes.py — ifc round-trip / ValueError
- tests/rules/test_library.py — new factories
- tests/rules/test_engine.py — all_of / named_equals
- tests/persistence/ — ADD COLUMN + SQL round-trip
- tests/versioning/ — fingerprint includes ifc_type
- tests/test_public_surface.py — new rule names in export list if required
```

## Acceptance criteria

- [ ] `beam.attrs.ifc_type = "IfcBeam"` reads back on the fake; default is `""`
- [ ] Unknown set token raises `ValueError` naming the allow-list
- [ ] `ModelReader` copies `ifc_type`; SQL load/save round-trips it
- [ ] Opening a pre-column SQLite file adds `ifc_type` and then round-trips `""`
- [ ] `_attribute_fields` includes `ifc_type`; codec field-match still holds
- [ ] `ifc_type_is("IfcBeam")` fails empty/`"IfcWall"`; `material_is("Pine")` fails empty (unlike `material_in`)
- [ ] `count_is` and `all_of` / `named_equals` behave as Spec
- [ ] `dimensions_within` skip-missing and `material_in` empty-pass unchanged
- [ ] `batch_apply` still rejects `ifc_type`
- [ ] Isolation green (`bim_controller` only inside `cadwork_adapter`)
- [ ] Tests with fakes from architecture §5
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/element/test_attributes.py tests/rules/test_library.py tests/rules/test_engine.py tests/persistence/ tests/versioning/ tests/test_isolation.py tests/test_public_surface.py -q`
- **Runtime exercise:** `uv run pytest tests/element/test_attributes.py tests/rules/test_library.py tests/persistence/ tests/versioning/ -k "ifc_type or material_is or count_is or attribute"` — US-3 factories, US-10, US-11
- **Inner-loop:** `uv run pytest tests/element/test_attributes.py tests/rules/test_library.py -k "ifc or material_is or count_is" -q`
- **Graphical / Manual:** none

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Run implement — it switches to this seed’s `**Branch:**` itself.
3. You own commits and pushes on this seed branch (plugin does not push seed branches).

```
/lp-to-implement @docs/sessions/gherkin-live-model-tests/01-ifc-snapshot.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/gherkin-live-model-tests/01-ifc-snapshot.md @docs/sessions/gherkin-live-model-tests/BOARD.md @docs/spec/gherkin-live-model-tests.md @docs/architecture/gherkin-live-model-tests.md
```

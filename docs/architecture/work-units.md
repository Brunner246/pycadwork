# Architecture: Work units for bulk live-model mutations

> **Source Spec:** `docs/spec/work-units.md`
> **Source research:** `docs/research/work-units.md`
> **Status:** Draft
>
> Every decision below cites Spec §, research `file:line`, or is labeled `[NEW]` (rules in §10).

## 1. Context

This plan adds one deep module — `pycadwork.work.WorkUnit` — that turns a
tracked set of live elements plus a sequence of `apply` / `run` steps into a
compensating transaction over **attributes**, then optionally registers the
result on cadwork's Undo stack. Hexagonal shape is inherited from the package:
the new module sits in the domain layer, talks only to the existing
`cadwork_adapter` seam, and is proven against `FakeCadworkAdapter`. No new
Protocol is introduced; callers depend on the class, matching
`DisplayRefreshScope`, `Document`, and `ModelVersioning`.

See Spec `## Solution` and research `## Context`.

## 2. System shape (hexagonal map)

```text
Driving adapters                         Domain core                         Driven adapters
────────────────                         ───────────                         ───────────────
plugin / script / examples  ──►  WorkUnit  ──►  cadwork.elements     ──►  ElementsAdapter
                                 │              cadwork.attributes         FakeElementsAdapter
                                 │              cadwork.display            DisplayAdapter / fake
                                 ├── batch_apply (reuse)
                                 ├── DisplayRefreshScope (reuse)
                                 └── WorkReport (pure DTOs)
```

### 2.1 Driving (primary) ports — what callers do

There is no separate Protocol. The **public surface is the class** (package
convention; Spec Implementation Decisions — Module and names).

| Port (conceptual) | Shape (key methods) | Source |
|-------------------|---------------------|--------|
| `WorkUnit` | `__enter__` / `__exit__`; `track`; `apply(**attrs)`; `run(fn, *, name=)`; `.report`; `.elements` | Spec Implementation Decisions — `WorkUnit` API |
| `WorkReport` / `WorkStep` / `AttributeDiff` / `WorkStatus` | frozen read-only result | Spec Implementation Decisions — Report DTOs |

### 2.2 Driven (secondary) ports — what the core needs from outside

| Port | Shape | Test double | Source |
|------|-------|-------------|--------|
| `cadwork.elements` | existing + **`[NEW]`** `add_modified_elements_to_undo(eids)` | `FakeElementsAdapter` | Spec Adapter seam; research finding 4 (`_elements.py` has no undo today) |
| `cadwork.attributes` | existing get/set used by `batch_apply` and snapshot reads via `Element.attrs` | `FakeAttributesAdapter` | research `_batch.py:10-41`; `attributes.py` |
| `cadwork.display` | existing disable / recreate / enable, driven by `DisplayRefreshScope` | `FakeDisplayAdapter` | research `_display.py:50-56` |

No new driven-port type. The seam stays the `cadwork` facade singleton.

### 2.3 Adapters

| Adapter | Implements port | Tech | Reuses |
|---------|-----------------|------|--------|
| `ElementsAdapter` | `cadwork.elements` | cwapi3d `element_controller` | existing class; **`[NEW]`** one method |
| `FakeElementsAdapter` | same | in-memory `FakeState` list | existing fake; **`[NEW]`** `modified_undo_calls` |
| `AttributesAdapter` / fake | `cadwork.attributes` | cwapi3d `attribute_controller` | research Reusable building blocks |
| `DisplayAdapter` / fake | `cadwork.display` | cwapi3d `utility_controller` / `element_controller.recreate_elements` | `DisplayRefreshScope` |

### 2.4 Cross-factory port contracts

n/a — no story spans repos.

## 3. Deep modules

### 3.1 `WorkUnit` (`pycadwork.work`)

- **Interface (what callers see):**
  - `WorkUnit(elements=(), *, undo=True)` as a context manager
  - `track(elements)`, `apply(**attrs)`, `run(fn, *, name=None)`
  - `report: WorkReport` (frozen only after `__exit__`; `RuntimeError` before)
  - `elements: tuple[Element, ...]`
- **Hidden complexity:** attribute snapshot at enter/track over `_BATCH_SETTERS`;
  inner `DisplayRefreshScope`; compensating restore grouped by `(attribute, value)`
  through `batch_apply`; success-path undo registration; per-step diffs vs enter
  (or track-time) snapshot; reject `apply`/`run`/`track` outside the active
  context.
- **Why deep, not shallow:** the caller names a block and two verbs; the module
  owns snapshot, restore, display, undo, and the report so none of those leak
  into plugin code.
- **Source:** Spec Implementation Decisions — `WorkUnit` API; research findings
  2–5.

### 3.2 Report DTOs (`pycadwork.work`)

- **Interface:** frozen `WorkStatus`, `AttributeDiff`, `WorkStep`, `WorkReport`
  (with flattened `.diffs`).
- **Hidden complexity:** none — pure values.
- **Why deep enough:** keep report types next to the unit that produces them,
  not in `pycadwork.reporting` (quantity takeoff over `ModelSnapshot`).
- **Source:** Spec Report DTOs; research finding 7 (`reporting/records.py:21-55`
  as shape precedent only).

### 3.3 `ElementsAdapter.add_modified_elements_to_undo` (seam extension)

- **Interface:** `add_modified_elements_to_undo(eids: list[ElementId]) -> None`
- **Hidden complexity:** the live call is a thin `element_controller` passthrough;
  the fake records `list(eids)` on `FakeState.modified_undo_calls`.
- **Why here, not `OperationsAdapter`:** cwapi3d places
  `add_modified_elements_to_undo` on `element_controller`; `OperationsAdapter`
  already owns boolean `subtract_elements_with_undo` only
  (`_operations.py:37-50`). A third UndoAdapter would split the seam without
  a second controller.
- **Source:** Spec Adapter seam; research finding 4. **`[NEW]`** method on an
  existing adapter.

## 4. SOLID review (per module)

| Module | SRP — single reason to change | OCP — open for ext / closed for mod | LSP — contract for substitutes | ISP — port small per client | DIP — domain depends on ports only |
|--------|-------------------------------|-------------------------------------|--------------------------------|-----------------------------|-------------------------------------|
| `WorkUnit` | One reason: run a tracked live-model unit (snapshot / apply / run / restore / undo / report) | New attribute keys arrive by extending `_BATCH_SETTERS` + attrs, not by subclassing `WorkUnit` | Fake cadwork substitutes for live cadwork; `WorkUnit` cannot tell | Callers see CM + three verbs; restore/undo/display stay private | Imports `cadwork` facade + `batch_apply` / `DisplayRefreshScope`; never `element_controller` |
| Report DTOs | One reason: describe a finished unit | New fields are additive on frozen types | Values, not substitutes | Read-only | No I/O |
| `ElementsAdapter` undo method | One reason: register modified ids on cadwork undo | Further undo verbs (`add_created`, `make_undo`) stay out until a later spec | Fake method matches live signature | One method, list of ids | Adapter is the I/O boundary |

## 5. Fake-first test strategy

- **Default policy:** `WorkUnit` tests use the autouse `FakeCadworkAdapter`. No
  mocks of `batch_apply` except when the test's *property* is "one adapter call
  per attribute" (existing `test_batch.py` already covers that; work tests may
  wrap with `unittest.mock.patch` the same way). Prefer asserting model state
  and `FakeState.modified_undo_calls`.
- **Per-port doubles:** §2.2 — all existing fakes; extend `FakeElementsAdapter`
  / `FakeState` in `src/pycadwork/testing/cadwork_adapter.py` (shipped fake,
  not a tests-only fork).
- **Direct-tested deep modules:** `WorkUnit` (`tests/work/test_unit.py`);
  report DTOs via those tests (no separate suite required).
- **Application-service-tested modules:** none.
- **Runtime verification of the real adapter:** v1 does **not** add a
  `/RUNPROGRAM` Ctrl+Z IT (Spec Testing Decisions). The live method is a
  one-line passthrough; isolation tests plus a future optional IT can cover it.
  Document that gap in `docs/work.md`.
- **Fake ownership:** continue `pycadwork.testing.cadwork_adapter`. Sessions
  must not roll a second fake.

## 6. Cross-cutting decisions

- **Concurrency / threading:** single-threaded, same as every live-model
  module. No locks. Nested `WorkUnit`s are unsupported (Spec Out of Scope;
  research Constraints).
- **Error handling:** exceptions, not result types. `TypeError` from
  `batch_apply` on unknown keys propagates after restore. `RuntimeError` if
  `apply` / `run` / `track` / `.report` are used outside the active context
  (Spec `WorkUnit` API). The original exception is re-raised after restore;
  restore failures should be chained (`raise ... from`) if a setter raises
  during compensation — **`[NEW]`** (Spec does not name the chaining; without
  it a restore error would swallow the caller's bug).
- **Logging / observability:** the `WorkReport` is the log. No logger.
- **Configuration / wiring:** `WorkUnit(...)` constructs its own inner
  `DisplayRefreshScope` and reads the `cadwork` singleton at call time (so
  tests' monkeypatch works). No DI container.
- **ABI / packaging:** new public exports on `pycadwork`; no extra dependency.
  `batch_apply` remains. Snapshot keys are imported from
  `pycadwork.utility._batch._BATCH_SETTERS` — do not duplicate the dict.
- **Display:** restore runs **before** delegating to
  `DisplayRefreshScope.__exit__`, so a raised unit skips recreate
  (research `_display.py:50-56`).

## 7. Out of scope (architectural)

- A `WorkPort` / `UnitOfWork` Protocol over `WorkUnit`
- Moving live-model units into `persistence.UnitOfWork`
- Compensating create / delete / boolean / geometry (no point setter;
  research `mappers.py:24-28`)
- `make_undo` as failure compensation
- New `UndoAdapter` sub-facade
- Decorator / explicit `commit()` without `with`
- CSV / `pycadwork.reporting` integration

## 8. Open questions

(none)

## 9. References

- Spec: `docs/spec/work-units.md`
- Research: `docs/research/work-units.md`
- Package architecture overview: `docs/architecture.md`
- Domain docs: `docs/utilities.md`, `docs/persistence.md`, `docs/testing.md`
- cwapi3d: `element_controller.add_modified_elements_to_undo`

## 10. Reuse audit (REQUIRED — every capability classified)

### 10.1 What was searched

| Repo | Searched for | Found / Not found |
|------|--------------|-------------------|
| pycadwork | `UnitOfWork` | `src/pycadwork/persistence/unit_of_work.py:50` — SQL records only |
| pycadwork | `batch_apply`, `_BATCH_SETTERS` | `src/pycadwork/utility/_batch.py:10-41` |
| pycadwork | `DisplayRefreshScope` | `src/pycadwork/utility/_display.py:23-80` |
| pycadwork | `add_modified_elements_to_undo`, `make_undo` | not on `ElementsAdapter`; boolean `subtract_elements_with_undo` only (`_operations.py:37-50`) |
| pycadwork | compensating rollback / work unit / transaction over elements | not found (mappers explicitly "no model rollback", `mappers.py:24-28`) |
| pycadwork | frozen report DTOs | `src/pycadwork/reporting/records.py:21-55` — BOM rows, wrong domain |
| pycadwork | `FakeElementsAdapter` / `FakeState` call lists | `src/pycadwork/testing/cadwork_adapter.py:258-282, 378+` |
| pycadwork | example tour `MODULES` | `examples/__init__.py:60-78` |

### 10.2 Classification

| Capability | Verdict | Source / Rationale |
|------------|---------|--------------------|
| `batch_apply` / `_BATCH_SETTERS` | **Reuse** | `utility/_batch.py` — `WorkUnit.apply` and restore write path |
| `DisplayRefreshScope` | **Reuse** | `utility/_display.py` — inner scope of `WorkUnit` |
| `Element.attrs` | **Reuse** | `element/components/attributes.py` — snapshot reads |
| `cadwork` facade | **Reuse** | `cadwork_adapter` — only seam |
| `FakeCadworkAdapter` / `FakeState` | **Reuse** (extend) | `testing/cadwork_adapter.py` — add `modified_undo_calls` |
| Frozen dataclass report shape | **Reuse** (pattern) | `reporting/records.py` — copy the *shape*, not the module |
| Example / docs wiring | **Reuse** (pattern) | `examples/__init__.py`, `docs/*.md` |
| `WorkUnit` + `pycadwork.work` | **`[NEW]`** | Searched `persistence.UnitOfWork`, `utility`, `ops`; SQL UoW does not wrap live mutations; `batch_apply` has no snapshot/undo/report; ops undo is boolean-only |
| `WorkReport` / `WorkStep` / `AttributeDiff` / `WorkStatus` | **`[NEW]`** | Searched `reporting.records`; those rows are takeoff over `ModelSnapshot`, not a unit journal |
| `ElementsAdapter.add_modified_elements_to_undo` | **`[NEW]`** | Searched adapters; only `subtract_elements_with_undo` exists. cwapi3d method lives on `element_controller`, so extend `ElementsAdapter` rather than invent `UndoAdapter` |
| Restore exception chaining | **`[NEW]`** | Spec says re-raise after restore; chaining (`from`) is the Python convention so a setter failure during compensation does not hide the original error |

### 10.3 Reuse-first rule for downstream slicing

Seeds must not invent a second bulk-apply helper, a second display-scope, a
SQL-shaped `UnitOfWork` for the live model, or a new undo sub-adapter.
Implement `WorkUnit` on top of `batch_apply` + `DisplayRefreshScope`; add one
method to the existing elements adapter and its shipped fake; keep report types
inside `pycadwork.work`.

# Research: work-units

## Context

Plugin and script authors already have two nearby tools for bulk live-model
work: `batch_apply` (one adapter call per attribute, no rollback) and
`DisplayRefreshScope` (viewport suppression, no rollback). Persistence has a
Fowler `UnitOfWork`, but it sequences **SQL records** in a SQLite transaction —
it does not wrap live cadwork mutations. There is no public type that runs a
sequence of functions against the live model, restores attributes if a step
fails, registers the successful unit on cadwork's Undo stack, and returns a
structured report of what changed.

This plan adds that type as a new top-level module (`pycadwork.work`), without
changing the SQL unit of work.

## Scope of exploration

- `src/pycadwork/utility/_batch.py` and `utility/_display.py`
- `src/pycadwork/persistence/unit_of_work.py` and `persistence/mappers.py`
- `src/pycadwork/ops/boolean.py` (the only live-model `undo=` flag today)
- `src/pycadwork/cadwork_adapter/_elements.py`, `_operations.py`, `_facade.py`
- `src/pycadwork/testing/cadwork_adapter.py` (fake observables)
- `src/pycadwork/element/components/attributes.py`
- `src/pycadwork/reporting/records.py` (frozen-report precedent)
- `examples/utilities.py`, `examples/__init__.py`, `tests/test_examples.py`
- `docs/architecture.md`, `docs/utilities.md`, `docs/testing.md`
- cwapi3d `element_controller` undo surface (public docs)

## Key findings

1. **The SQL `UnitOfWork` is the wrong home.**
   `persistence/unit_of_work.py:50-140` stages `register_new` / `register_dirty`
   / `register_removed` records and commits them inside
   `GatewayConnection.transaction()`. Rollback discards the staged lists; it
   never talks to cadwork. Reusing the name `UnitOfWork` on the live model
   would collide in the top-level namespace (`pycadwork/__init__.py` already
   re-exports persistence types). A new class name (`WorkUnit`) in a new
   module is the clean split.

2. **`batch_apply` is the bulk-attr primitive to reuse, not replace.**
   `utility/_batch.py:10-41` maps a closed set of attribute names (`name`,
   `group`, `subgroup`, `comment`, `material_name`, `sku`, `production_number`,
   `part_number`) onto one adapter setter each and raises `TypeError` on
   unknowns. Tests in `tests/utility/test_batch.py` already lock that contract.
   A work-unit `apply(**attrs)` should call this helper so the supported-key
   set stays single-sourced.

3. **Display suppression exists and is exception-safe.**
   `DisplayRefreshScope.__exit__` (`utility/_display.py:50-56`) always
   re-enables refresh and **skips** `recreate_elements` when the block raised,
   so a compensating restore can run and the viewport is not rebuilt from
   half-applied state. The work-unit should wrap this scope rather than
   reimplement disable/enable.

4. **cadwork has no live-model transaction; undo is a post-hoc stack.**
   cwapi3d `element_controller` exposes `add_modified_elements_to_undo`,
   `add_created_elements_to_undo`, `add_elements_to_undo(ids, cmd)`,
   `make_undo`, and `make_redo`. None of these bracket an arbitrary Python
   sequence the way SQLite `BEGIN`/`COMMIT` does. The only live-model undo
   flag in pycadwork today is `ops.difference(..., undo=True)`
   (`ops/boolean.py:38-55`), which calls
   `cadwork.operations.subtract_elements_with_undo`
   (`cadwork_adapter/_operations.py:37-50`). Attribute writes have **no**
   undo registration. `ElementsAdapter` (`cadwork_adapter/_elements.py`) has
   create/delete/type/container methods and **no** undo methods.

5. **Geometry cannot be compensated with the current seam.**
   `persistence/mappers.py:24-28` states the standing constraint: there is no
   point setter, so existing elements' axes are never moved on write-back.
   Compensating rollback in v1 is therefore **attribute-only**, over the same
   keys `batch_apply` supports. Create/delete/boolean/geometry remain
   best-effort side effects of `run(fn)` with no restore guarantee.

6. **The fake is recording-style and the place to observe undo.**
   `FakeState` already keeps call lists for operations
   (`testing/cadwork_adapter.py:262-282`). Undo registration should follow
   that pattern (`modified_undo_calls: list[list[ElementId]]`) on
   `FakeElementsAdapter`, not try to emulate cadwork's real undo stack.

7. **Reports in this package are frozen slotted dataclasses.**
   `reporting/records.py:21-55` (`PartRow`, `MaterialTotalRow`) is the
   precedent: frozen, slots, plain scalars plus tuples. A `WorkReport` belongs
   in that family, not in `pycadwork.reporting` (which is quantity takeoff over
   a `ModelSnapshot`).

8. **Examples are a CI-enforced public-API tour.**
   `examples/__init__.py:60-78` lists `MODULES`; `tests/test_examples.py:19-23`
   imports each and calls `run()` against the autouse fake. A new
   `examples/work.py` must join that tuple. Module docs live as `docs/<topic>.md`
   (see `docs/utilities.md`, `docs/rules.md`); no package under `src/pycadwork/`
   currently ships its own README.

9. **Isolation rule is mechanical.**
   `tests/test_isolation.py` forbids importing `cadwork` / `*_controller`
   outside `cadwork_adapter`. The work module must call
   `pycadwork.cadwork_adapter.cadwork` only.

## Reusable building blocks

| Building block | Path | Role in this plan |
|----------------|------|-------------------|
| `batch_apply` | `src/pycadwork/utility/_batch.py` | `WorkUnit.apply` implementation; supported-key set and `TypeError` |
| `DisplayRefreshScope` | `src/pycadwork/utility/_display.py` | Inner scope of `WorkUnit`; recreate-on-success, skip-on-error |
| `_BATCH_SETTERS` keys | `utility/_batch.py:10-18` | Attribute snapshot / restore / diff vocabulary |
| `Attributes` properties | `src/pycadwork/element/components/attributes.py` | Read current values for the snapshot |
| Frozen report DTOs | `src/pycadwork/reporting/records.py` | Shape for `WorkReport` / `StepOutcome` / `AttributeDiff` |
| `FakeState` observables | `src/pycadwork/testing/cadwork_adapter.py` | Record `add_modified_elements_to_undo` calls |
| Example tour | `examples/__init__.py`, `tests/test_examples.py` | `examples/work.py` joins `MODULES` |
| Isolation test | `tests/test_isolation.py` | No extra wiring if work stays above the seam |
| Architecture layout table | `docs/architecture.md:51-66` | Add `pycadwork.work` row + mermaid node |
| cwapi3d undo | `element_controller.add_modified_elements_to_undo` | Success-path Ctrl+Z registration |

## Constraints & gotchas

- **Name collision.** `pycadwork.persistence.UnitOfWork` stays. The live-model
  type is `WorkUnit` in `pycadwork.work`. Docs must say so in the first
  paragraph.
- **`batch_apply` is not atomic internally.** It writes attributes in kwargs
  order and can raise mid-loop (`_batch.py:36-40`). The work-unit's snapshot
  restore is what makes `apply(name="X", colour="red")` safe.
- **Untracked mutations are invisible.** `run(fn)` that writes attributes on
  an element never passed to `WorkUnit(...)` / `track()` will not be restored
  and will not appear in diffs. No whole-document scan in v1.
- **cadwork undo is not nested and is not a transaction.**
  `add_modified_elements_to_undo` registers the current element state as an
  undo step; it does not snapshot Python-side intent. Failure rollback is
  compensating restore, **not** `make_undo`. Success registration happens
  only after all steps complete. `undo=False` skips the adapter call.
- **Do not call `make_undo` on failure.** That would undo whatever happened
  to be last on cadwork's stack, which may predate the unit.
- **Nested `WorkUnit`s are unsupported** in v1 (inner snapshot would capture
  already-mutated values).
- **`apply` / `run` only inside the context.** Calling them before `__enter__`
  has no snapshot; raise.
- **Fake cannot prove Ctrl+Z.** Tests assert the adapter was called with the
  tracked ids; they cannot emulate `make_undo` reversing attributes unless
  someone later teaches the fake that. Out of v1.

## Open questions

(none deferred — product decisions resolved in the grill.)

## Out of scope

- Changing `persistence.UnitOfWork` or the SQL transaction
- Compensating create / delete / boolean / geometry / axis moves
- Invertible Command objects as the public API
- Calling `make_undo` / `make_redo` from `WorkUnit`
- Whole-model attribute snapshots
- CSV export of `WorkReport`
- Deprecating `batch_apply` or folding it into `work`
- A decorator form of `WorkUnit` (elements are instance state)

## References

- [Element Controller — add_modified_elements_to_undo](https://docs.cadwork.com/projects/cwapi3dpython/en/latest/documentation/element_controller/)
- `docs/utilities.md` — `DisplayRefreshScope` and `batch_apply`
- `docs/persistence.md` — SQL `UnitOfWork`
- `docs/testing.md` — fake-adapter recipe
- `docs/architecture.md` — one-seam layout
- `examples/utilities.py` — current bulk-work teaching example

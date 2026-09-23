# Seed: WorkUnit + undo seam + unit tests

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
- **Branch:** `feature/work-units-01-work-unit`

## Source documents

- **Spec:** `docs/spec/work-units.md`
- **Research:** `docs/research/work-units.md`
- **Architecture:** `docs/architecture/work-units.md`
- **Verification:** `docs/verification/work-units.md`

## Scope (Definition of Ready)

Implement `pycadwork.work.WorkUnit` as a context manager over a tracked element
set: attribute snapshot at enter/`track`, `apply(**attrs)` via `batch_apply`,
`run(fn, *, name=)`, compensating restore on exception, success-path
`add_modified_elements_to_undo` (opt out with `undo=False`), frozen `WorkReport`.
Extend `ElementsAdapter` + shipped fake. Re-export public types. Fake-backed
unit tests for US-1–5, US-7, US-8.

## Spec guardrail

**In scope (verbatim):**

> Add `pycadwork.work`, a new public module whose centre is `WorkUnit`: a context manager over a tracked set of `Element`s. Inside the block the author calls `apply(**attrs)` (bulk attribute writes via existing `batch_apply`) and `run(fn, *, name=)`. On enter, the unit snapshots the `batch_apply` attributes of every tracked element. On exception it restores those snapshots, skips viewport recreate, does **not** touch cadwork Undo, records a rolled-back `WorkReport`, and re-raises. On success it recreates tracked elements once, registers them with `add_modified_elements_to_undo` (unless `undo=False`), and exposes a frozen `WorkReport`.

**Out of scope (verbatim):**

> Compensating create, delete, boolean, geometry, or axis moves. Invertible Command objects. `make_undo` / `make_redo` / `add_created_elements_to_undo`. Snapshotting the whole document. Nesting `WorkUnit`s. Decorator form / explicit `commit()` / `rollback()` without `with`. CSV writer. Changing or deprecating `batch_apply`, `DisplayRefreshScope`, or `persistence.UnitOfWork`. User-attribute (indexed) writes in `apply`. Module README and examples (seed 02).

If you cannot build this slice without violating the guardrail, STOP.

## Architectural guardrail

- **Driving port(s):** `WorkUnit` public class (no new Protocol)
- **Driven port(s) + test double:** `cadwork.elements` / `attributes` / `display` via existing `FakeCadworkAdapter`; **`[NEW]`** `add_modified_elements_to_undo` on `ElementsAdapter` + `FakeState.modified_undo_calls`
- **Deep module(s):** `WorkUnit`; report DTOs in `pycadwork.work`; one undo method on `ElementsAdapter`
- **SOLID / cross-cutting (verbatim):** Restore runs before delegating to `DisplayRefreshScope.__exit__`. Snapshot keys imported from `pycadwork.utility._batch._BATCH_SETTERS` — do not duplicate. Restore failures chain (`raise ... from`) so a setter error during compensation does not hide the original exception. `RuntimeError` if `apply` / `run` / `track` / `.report` are used outside the active context.
- **Out of scope (architecture §7):** A `WorkPort` Protocol; moving live-model units into `persistence.UnitOfWork`; compensating create/delete/boolean/geometry; `make_undo` as failure compensation; new `UndoAdapter`; decorator / explicit `commit()`; CSV / reporting integration

If this slice needs a `[NEW]` architectural decision, STOP and run `/lp-to-architecture` first.

## Reusable building blocks

- `src/pycadwork/utility/_batch.py` — `batch_apply` and `_BATCH_SETTERS`
- `src/pycadwork/utility/_display.py` — inner `DisplayRefreshScope`
- `src/pycadwork/element/components/attributes.py` — snapshot reads via `Element.attrs`
- `src/pycadwork/cadwork_adapter/_elements.py` — add undo method here
- `src/pycadwork/testing/cadwork_adapter.py` — extend `FakeState` / `FakeElementsAdapter`
- `src/pycadwork/reporting/records.py` — frozen slotted dataclass shape for reports
- `tests/utility/test_batch.py` — `_make_beam` helper pattern
- `tests/test_public_surface.py` — `VERSIONING_EXPORTS` pattern for `WORK_EXPORTS`
- `tests/conftest.py` — autouse fake

## Touched files (predicted)

```
- src/pycadwork/work/__init__.py — public re-exports
- src/pycadwork/work/unit.py — WorkUnit
- src/pycadwork/work/report.py — WorkStatus, AttributeDiff, WorkStep, WorkReport
- src/pycadwork/cadwork_adapter/_elements.py — add_modified_elements_to_undo
- src/pycadwork/testing/cadwork_adapter.py — FakeState.modified_undo_calls + fake method
- src/pycadwork/__init__.py — re-export WorkUnit, WorkReport, WorkStep, AttributeDiff, WorkStatus
- tests/work/__init__.py
- tests/work/test_unit.py — US-1–5, US-7, undo/report/track/context errors
- tests/test_public_surface.py — WORK_EXPORTS
```

## Acceptance criteria

- [ ] `with WorkUnit(beams) as work: work.apply(name="Stud")` persists attrs; `report.status is COMMITTED`
- [ ] Exception after a prior `apply` restores snapshot, re-raises, no undo call, `report.status is ROLLED_BACK`
- [ ] Mid-`apply` unknown kwarg still restores earlier keys in that call
- [ ] `run(fn)` return value and default step name (`__qualname__`) work; two runs roll back together
- [ ] Default undo records one `modified_undo_calls` entry with tracked ids; `undo=False` and rollback record none
- [ ] `track()` mid-block snapshots current attrs; restore does not rewind past track-time
- [ ] `apply` / `run` / `track` / `.report` outside the active context raise `RuntimeError`
- [ ] `WORK_EXPORTS` on `pycadwork` and in `__all__`
- [ ] Isolation still green (`pycadwork.work` does not import `cadwork` / `*_controller`)
- [ ] Tests with fakes from architecture §5
- [ ] Spec + architecture out-of-scope respected

## Verification

- **Full pipeline:** `uv run pytest tests/work/ tests/test_public_surface.py tests/test_isolation.py -q`
- **Runtime exercise:** `uv run pytest tests/work/ -q` — US-1–5, US-7, US-8 (undo + isolation)
- **Inner-loop:** `uv run pytest tests/work/test_unit.py -q`
- **Graphical / Manual:** none

## First steps for this session

1. `@`-attach this seed + BOARD + Spec + architecture (+ research/verification if present).
2. Run implement — it switches to this seed’s `**Branch:**` itself.
3. You own commits and pushes on this seed branch (plugin does not push seed branches).

```
/lp-to-implement @docs/sessions/work-units/01-work-unit.md @docs/sessions/work-units/BOARD.md @docs/spec/work-units.md @docs/architecture/work-units.md
```

Or AFK:

```
/lp-autopilot-run --implement @docs/sessions/work-units/01-work-unit.md @docs/sessions/work-units/BOARD.md @docs/spec/work-units.md @docs/architecture/work-units.md
```

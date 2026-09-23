# Spec: Work units for bulk live-model mutations

## Problem Statement

A plugin author who wants to rename a set of elements, run a couple of follow-up
functions, put the whole thing on cadwork's Undo stack, and log what changed
today has to hand-roll four concerns: `batch_apply`, `DisplayRefreshScope`,
compensating restore if a step raises, and an adapter call that does not exist
yet (`add_modified_elements_to_undo`). Missing any one of them leaves a
half-renamed model, a viewport that repainted N times, or a change the user
cannot Ctrl+Z. Persistence `UnitOfWork` does not help — it commits SQL records,
not live elements.

## Solution

Add **`pycadwork.work`**, a new public module whose centre is `WorkUnit`: a
context manager over a tracked set of `Element`s.

Inside the block the author calls `apply(**attrs)` (bulk attribute writes via
existing `batch_apply`) and `run(fn, *, name=)` (arbitrary callables). On
enter, the unit snapshots the `batch_apply` attributes of every tracked
element. On exception it restores those snapshots, skips viewport recreate,
does **not** touch cadwork Undo, records a rolled-back `WorkReport`, and
re-raises. On success it recreates tracked elements once, registers them with
`add_modified_elements_to_undo` (unless `undo=False`), and exposes a frozen
`WorkReport` of per-step status and before/after attribute diffs.

Create, delete, boolean, and geometry are not compensated in v1. Callables may
still run; only tracked attributes are restored.

```python
from pycadwork import WorkUnit

with WorkUnit(beams) as work:
    work.apply(name="Stud", group="frame")
    work.run(relabel_openings, name="openings")
print(work.report.status)          # committed
for diff in work.report.diffs:
    print(diff.element_id, diff.attribute, diff.before, diff.after)
```

## User Stories

1. **As a** plugin author, **I want** to set the same attributes on many
   elements inside one work-unit, **so that** a typo or mid-loop error leaves
   every tracked element as it was, not half-renamed.

2. **As a** plugin author, **I want** to run a sequence of callables in that
   same unit, **so that** several small functions behave as one all-or-nothing
   bulk job over the tracked set.

3. **As a** cadwork user of a plugin, **I want** a successful unit to appear as
   one Undo step, **so that** Ctrl+Z reverts the bulk rename (and I can opt
   the script out with `undo=False`).

4. **As a** plugin author, **I want** a frozen report of what the unit did
   (committed vs rolled back, per-step outcome, attribute diffs), **so that** I
   can log, assert, or print the change without scraping the model again.

5. **As a** plugin author, **I want** to register extra elements with
   `track()` after the unit has started, **so that** a callable that discovers
   related parts can bring them under the same snapshot/undo/report.

6. **As a** reader of the package, **I want** a module doc (`docs/work.md`) and
   a runnable example (`examples/work.py`) on the CI example tour, **so that**
   the new module is taught the same way as utilities, rules, and reporting.

7. **As a** test author, **I want** the suite to prove commit, rollback,
   undo-flag, diffs, and `TypeError` on unknown attributes against
   `FakeCadworkAdapter`, **so that** CI never needs a live cadwork process.

8. **As a** maintainer, **I want** undo registration to go through
   `cadwork.elements` on the one seam, **so that** isolation tests stay green
   and the fake can record the call.

## Implementation Decisions

### Module and names

| Item | Decision |
|------|----------|
| Package | `src/pycadwork/work/` |
| Public types | `WorkUnit`, `WorkReport`, `WorkStep`, `AttributeDiff`, `WorkStatus` |
| Not named `UnitOfWork` | That name stays on `pycadwork.persistence.UnitOfWork` |
| Re-export | `from pycadwork import WorkUnit, WorkReport, …` and `__all__` |
| `batch_apply` | Unchanged public helper; `WorkUnit.apply` calls it |

### `WorkUnit` API

```python
class WorkUnit:
    def __init__(
        self,
        elements: Iterable[Element] = (),
        *,
        undo: bool = True,
    ) -> None: ...

    def track(self, elements: Element | Iterable[Element]) -> None: ...
    def apply(self, **attrs: object) -> None: ...
    def run(self, fn: Callable[[], object], *, name: str | None = None) -> object: ...

    @property
    def report(self) -> WorkReport: ...
    @property
    def elements(self) -> tuple[Element, ...]: ...
```

- **Context manager required.** `apply` / `run` / `track` (for snapshotting)
  raise `RuntimeError` if called before `__enter__`. After `__exit__` they
  raise as well (the unit is finished).
- **`track`** adds elements not already in the set, snapshots their *current*
  `batch_apply` attributes, and registers them on the inner
  `DisplayRefreshScope`.
- **`apply`** is `batch_apply(self.elements, **attrs)` plus a `WorkStep` named
  `apply` (include the kwarg keys in the step name, e.g. `apply:name,group`).
  Empty tracked set is a no-op, same as `batch_apply`.
- **`run`** calls `fn()` with no arguments. Default step name is
  `fn.__qualname__`. The return value is passed through. `fn` is responsible
  for closing over whatever it needs (typically the tracked elements).
- **Inner `DisplayRefreshScope`.** `__enter__` starts one and `track`s the
  initial set. `__exit__` delegates to it so success recreates once and
  failure skips recreate.
- **Success path.** If `undo` is true, call
  `cadwork.elements.add_modified_elements_to_undo(list of tracked ids)`.
  Then freeze `WorkReport(status=COMMITTED, ...)`.
- **Failure path.** Restore every snapshotted attribute (per element, via the
  same setters `batch_apply` uses), freeze
  `WorkReport(status=ROLLED_BACK, ...)`, do **not** call undo registration,
  re-raise. Restore even if the failing call was `apply` itself (unknown key
  after a earlier kwarg already wrote).
- **No `make_undo`.** Failure compensation is the attribute snapshot, not
  cadwork's undo stack.
- **No decorator form** and **no nested units** in v1.

### Snapshot vocabulary

Exactly the keys in `utility/_batch.py` `_BATCH_SETTERS`. Reading goes through
`Element.attrs` (or the adapter getters those properties wrap). Restoring
groups by `(attribute, value)` and calls `batch_apply` so the write path stays
identical to a forward `apply`.

### Report DTOs

Frozen, slotted dataclasses, sibling in spirit to `PartRow`:

```python
class WorkStatus(enum.Enum):
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"

@dataclass(frozen=True, slots=True)
class AttributeDiff:
    element_id: int
    attribute: str
    before: object
    after: object

@dataclass(frozen=True, slots=True)
class WorkStep:
    name: str
    status: WorkStatus
    diffs: tuple[AttributeDiff, ...]

@dataclass(frozen=True, slots=True)
class WorkReport:
    status: WorkStatus
    element_ids: tuple[int, ...]
    steps: tuple[WorkStep, ...]

    @property
    def diffs(self) -> tuple[AttributeDiff, ...]:
        """Flatten every step's diffs in step order."""
```

- Diffs record attributes whose current value after the step differs from the
  value at **unit enter** (or at `track` time for late-tracked elements), not
  from the previous step. That keeps rollback diffs aligned with the snapshot
  that will actually be restored.
- On rollback, each completed step stays in `steps` with
  `status=ROLLED_BACK`; the failing step is recorded with its name and
  `ROLLED_BACK` as well (diffs up to the failure). `report.status` is
  `ROLLED_BACK`.
- `report` is readable after the `with` block. During the block it may be
  incomplete; the frozen value is assigned in `__exit__`. Reading `.report`
  before exit returns the in-progress view or raises — **raise
  `RuntimeError` until `__exit__` has frozen it**, so tests and examples
  always read the finished report.

### Adapter seam

Add to `ElementsAdapter` and `FakeElementsAdapter`:

```python
def add_modified_elements_to_undo(self, eids: list[ElementId]) -> None: ...
```

Live adapter calls `element_controller.add_modified_elements_to_undo`. The
fake appends `list(eids)` to `FakeState.modified_undo_calls`. Do **not** add
`make_undo` / `add_created_elements_to_undo` in v1 unless a test strictly
needs them.

### Docs and examples (the requested README + examples)

| File | Change |
|------|--------|
| `docs/work.md` | Module README: problem, `WorkUnit` tour, report, limitations (untracked, no geometry rollback, vs SQL `UnitOfWork`) |
| `examples/work.py` | `demo_*` functions + `run()`: apply, run, rollback, undo=False, report diffs |
| `examples/__init__.py` | Append `"work"` to `MODULES` |
| `examples/README.md` | Table row |
| `README.md` | Topic table row |
| `docs/README.md` | “Working with the model” bullet |
| `docs/architecture.md` | Package-layout row + mermaid node |
| `src/pycadwork/__init__.py` | Re-exports |

`docs/work.md` **is** the module README. Do not add `src/pycadwork/work/README.md`;
no other module uses that pattern.

### Public-surface test

Extend `tests/test_public_surface.py` with a `WORK_EXPORTS` tuple mirroring
`VERSIONING_EXPORTS`.

## Testing Decisions

Fake-first; no live cadwork. New tests live under `tests/work/`.

| Layer | What | How |
|-------|------|-----|
| Unit | `apply` writes via one adapter call per attribute; unknown key `TypeError`; empty set is no-op | `tests/work/test_unit.py` + existing `batch_apply` behaviour |
| Unit | Successful `with` leaves new attrs, `report.status is COMMITTED`, diffs match before/after | fake elements |
| Unit | Exception in `apply` or `run` restores snapshot; exception propagates; no undo call; `report.status is ROLLED_BACK` | raise after a prior `apply` |
| Unit | Mid-`apply` typo (`name=` then unknown kwarg) still restores `name` | kwargs order |
| Unit | `undo=True` (default) records one `modified_undo_calls` entry with tracked ids; `undo=False` records none | `FakeState` |
| Unit | `track()` mid-block snapshots current attrs of the new element only | restore does not rewind that element past track-time |
| Unit | `apply`/`run`/`track` outside the context raise `RuntimeError` | |
| Unit | `run(fn)` return value is passed through; default step name is `__qualname__` | |
| Adapter | `FakeElementsAdapter.add_modified_elements_to_undo` exists and records | can live in `tests/work/` or adapter tests |
| Isolation | `pycadwork.work` does not import `cadwork` / `element_controller` | existing `test_isolation.py` |
| Public surface | `WorkUnit`, `WorkReport`, `WorkStep`, `AttributeDiff`, `WorkStatus` re-exported and in `__all__` | `test_public_surface.py` |
| Examples | `examples.work.run()` against the fake | `MODULES` + `test_examples.py` |

No real-cadwork integration test in v1: Ctrl+Z cannot be asserted on the fake,
and proving it would need a `/RUNPROGRAM` script out of proportion to
attribute restore.

## Out of Scope

- Compensating create, delete, boolean, geometry, or axis moves
- Invertible Command objects as the caller-facing API
- `make_undo` / `make_redo` / `add_created_elements_to_undo`
- Snapshotting the whole document
- Nesting `WorkUnit`s
- Decorator form / explicit `commit()` / `rollback()` without `with`
- CSV writer for `WorkReport`
- Changing or deprecating `batch_apply`, `DisplayRefreshScope`, or
  `persistence.UnitOfWork`
- User-attribute (indexed) writes in `apply` (not in `_BATCH_SETTERS`)

## Further Notes

- Suggested plan slug: `work-units`.
- Keep `WorkUnit` above the seam; the only new cwapi3d call is
  `add_modified_elements_to_undo`.
- Document in `docs/work.md`, in the first screenful, that this is **not**
  `persistence.UnitOfWork`.

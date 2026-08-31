# Work units: bulk live-model mutations

`WorkUnit` is a context manager over a tracked set of **live** cadwork
elements. It is **not** `persistence.UnitOfWork` — that type commits SQL
records. This one snapshots attributes, writes them in bulk, restores them
if a step raises, optionally registers one cadwork Undo step, and freezes a
`WorkReport`.

Today, doing a bulk rename that the user can Ctrl+Z — and that does not leave
the model half-updated if a later step raises — means hand-rolling
`batch_apply`, `DisplayRefreshScope`, compensating restore, and
`add_modified_elements_to_undo`. Missing any one of those leaves a
half-renamed model, a viewport that repainted N times, or a change the user
cannot undo. `WorkUnit` is that bundle.

```python
from pycadwork import WorkUnit

with WorkUnit(beams) as work:
    work.apply(name="Stud", group="frame")
    work.run(relabel_openings, name="openings")
print(work.report.status)          # committed
for diff in work.report.diffs:
    print(diff.element_id, diff.attribute, diff.before, diff.after)
```

## Tour

Construct with the elements to track, then enter a `with` block. `apply` /
`run` / `track` raise `RuntimeError` outside that block — including after
exit. The frozen `.report` is only readable after the block exits.

- **`apply(**attrs)`** writes the same attributes onto every tracked element
  via `batch_apply`. An empty tracked set is a no-op. Unknown keys raise
  `TypeError` (and still restore any kwargs that already wrote).
- **`run(fn, *, name=)`** calls `fn()` with no arguments. `fn` closes over
  whatever it needs (typically the tracked elements). The default step name
  is `fn.__qualname__`; the return value is passed through.
- **`track(elements)`** adds elements discovered mid-block. Their *current*
  attributes are snapshotted at track-time, so rollback does not rewind them
  past that moment.

On enter, the unit snapshots every tracked element's `batch_apply`
attributes (`name`, `group`, `material_name`, …) and starts an inner
`DisplayRefreshScope`. On success it recreates the tracked elements once
and, unless you passed `undo=False`, registers their ids with
`add_modified_elements_to_undo`. On exception it restores those snapshots,
skips viewport recreate, does **not** touch cadwork Undo, freezes a
rolled-back report, and re-raises.

```python
with WorkUnit(beams, undo=False) as work:
    work.apply(name="preview")
# committed, but cadwork's Undo stack was not touched
```

`track` after enter is how a callable that finds related parts brings them
under the same snapshot / undo / report:

```python
with WorkUnit(beams) as work:
    work.apply(group="frame")
    work.track(openings_of(beams))
    work.apply(name="opening")
```

## The report

After the `with` block, `.report` is a frozen `WorkReport`:

| Field | Meaning |
|-------|---------|
| `status` | `WorkStatus.COMMITTED` or `WorkStatus.ROLLED_BACK` |
| `element_ids` | tracked ids, in track order |
| `steps` | one `WorkStep` per `apply` / `run` (name, status, diffs) |
| `diffs` | every step's diffs, flattened, versus the **enter/track snapshot** |

Diffs are not step-to-step. They compare current values to the snapshot that
rollback would restore. On rollback, completed steps stay in `steps` with
`ROLLED_BACK`, and the failing step is recorded the same way.

## Limitations

- **Untracked mutations are invisible.** A `run(fn)` that writes attributes
  on an element never passed to `WorkUnit(...)` / `track()` is not restored
  and does not appear in diffs. There is no whole-document scan.
- **No geometry, create, delete, or boolean compensation.** Callables may
  still run; only snapshotted `batch_apply` attributes are restored.
- **Not `persistence.UnitOfWork`.** That type sequences SQL writes. This type
  mutates live elements. See [Persistence](persistence.md) for the SQL one.
- **cadwork Undo is not a Python transaction.** Success registers the current
  element state as one Undo step. Failure compensation is the attribute
  snapshot, not `make_undo`. Tests assert the adapter was called with the
  tracked ids; they cannot press Ctrl+Z in a live cadwork process.
- **No nested units**, no decorator form, and no `commit()` / `rollback()`
  without `with`.

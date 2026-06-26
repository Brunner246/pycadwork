# Reporting: cutting lists & material totals

`pycadwork.reporting` is the quantity-takeoff layer: pure functions over the
same `ModelSnapshot` the persistence layer reads and writes. Because both
sources produce a snapshot, every report runs identically against the **live
model** (`ModelReader().read()`) or a **pulled SQL store**
(`load_snapshot(connection, guid)`) — and the module itself never touches
cadwork or SQL, so it is unit-testable from record literals.

`cutting_list` collapses identical parts — same type, material, name, and
dimensions rounded to `precision` — into one counted row; `material_totals`
sums count/volume/weight per material. Both default to the path-anchored stock
(`beam`, `plate`, MEP runs) and carry the aggregated element ids for
traceability:

```python
from pycadwork import cutting_list, material_totals
from pycadwork.persistence import ModelReader

snapshot = ModelReader().read()

for row in cutting_list(snapshot):
    print(f"{row.count}x {row.name} {row.material_name} "
          f"{row.length:.0f} x {row.width:.0f} x {row.height:.0f}")

for row in material_totals(snapshot):
    print(row.material_name, row.count, row.total_volume)
```

Grouping is **composable**, not a set of hardcoded report variants. Each
`by_*` factory yields one `Dimension` axis (a label plus a key function), and
a report groups by the tuple of the axes you pass:

```python
from pycadwork import by_cover, by_material, by_storey, cutting_list

# per storey AND per material, in one pass
rows = cutting_list(snapshot, dimensions=(by_storey(), by_material()))
rows[0].group  # ("Building A/S0", "Pine")

# per owning wall/slab/roof — pass the field carrying the membership link,
# since the snapshot does not store the project's active grouping mode
rows = cutting_list(snapshot, dimensions=(by_cover(link="group"),))
```

A custom axis is one `Dimension(label, key_fn)` — no changes to the report
functions. For files, the stream-based stdlib-csv writers
(`pycadwork.reporting.write_parts_csv` / `write_material_totals_csv`) expand
each dimension into one labelled column. A runnable tour lives in
[`examples/reporting.py`](../examples/reporting.py).

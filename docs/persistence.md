# Persistence: mirror the model to SQL

`pycadwork.persistence` maps the running cadwork document into a **normalized
(3NF) SQL database** and back. It uses the classic Fowler PoEAA patterns —
**Table Data Gateways** (one per table), a **Unit of Work** that sequences writes
in a single transaction, frozen **record** DTOs as the lingua franca, and
**mappers** (`ModelReader` / `ModelWriter`) that are the sole cadwork seam. Like
the rest of the package it never imports cwapi3d — it reads and writes the model
only through `Document` / `Element` and the adapter.

The sync is **bidirectional via two explicit operations** — `pull()` (model →
SQL) and `push()` (SQL → model). There is no automatic conflict-merge: the
direction is always your choice. The default backend is stdlib `sqlite3` behind
a pluggable `GatewayConnection` Protocol — **no new dependency**.

## Snapshot the model into SQL — `pull`

`open_sqlite` opens (or creates) a database and applies the schema — twelve
tables: `project`, `element`, `attribute`, `geometry`, `user_attribute`,
`cover`, `container_member`, `building`, `storey`, `storey_assignment`,
`material`, `element_material`. `pull` is
idempotent (upsert by `(project_guid, element_id)`) and deletes rows for elements
that have left the model:

```python
from pycadwork import Synchronizer, open_sqlite

connection = open_sqlite("model.db")  # or open_sqlite(":memory:")
report = Synchronizer().pull(connection)  # model -> SQL, in one transaction
print(report.created, report.updated, report.deleted)

# re-pull after edits: unchanged rows update in place, gone elements are pruned
Synchronizer().pull(connection)
```

## Rebuild a model from SQL — `push`

`push` loads the stored snapshot, diffs it against the live model, then creates
missing elements from their stored geometry, updates the existing ones (attrs,
dims, cover kind, grouping, building/storey, container membership), and deletes
removed rows. cadwork assigns fresh ids on create, so the writer threads a
`stored → model` id map through every dependent link:

```python
from pycadwork import Synchronizer, open_sqlite

connection = open_sqlite("model.db")
report = Synchronizer().push(connection)  # SQL -> model (display-suppressed)
print(f"created={report.created} updated={report.updated} "
      f"deleted={report.deleted} skipped={report.skipped}")
```

A pull immediately followed by a push is a no-op (every element already exists);
types with no faithful `create_*` path are skipped with a warning and counted in
`report.skipped`.

## Read a snapshot without touching SQL — `ModelReader`

`ModelReader.read()` projects the live model into an in-memory `ModelSnapshot` of
frozen records — useful for inspection, diffing, or feeding your own store:

```python
from pycadwork.persistence import ModelReader

snapshot = ModelReader().read()

for element in snapshot.elements:
    print(element.id, element.element_type)  # e.g. 1 'beam'

geometry = snapshot.geometry_by_element()  # dict[int, GeometryRecord]
geometry[some_id].width, geometry[some_id].length
snapshot.members_by_container()  # dict[int, list[int]]
```

## Diff two snapshots — `load_snapshot` + `diff`

The diff is pure and keyed by element id, so you can compute exactly what a push
*would* do before doing it:

```python
from pycadwork import Document
from pycadwork.persistence import ModelReader, diff, load_snapshot

target = load_snapshot(connection, Document().guid)  # what SQL holds
current = ModelReader().read()  # what the model holds

delta = diff(current, target)
print(delta.new_ids)  # ids to create on push
print(delta.dirty_ids)  # ids to update
print([r.id for r in delta.removed])  # ids to delete
```

## Drive the gateways and unit of work directly

For finer control, talk to the gateways and the `UnitOfWork` yourself. Every
staged change commits in one transaction; any error rolls the whole thing back:

```python
from pycadwork.persistence import UnitOfWork, open_sqlite
from pycadwork.persistence.gateways import ElementGateway
from pycadwork.persistence.records import ElementRecord, ProjectRecord

connection = open_sqlite("model.db")

unit = UnitOfWork(connection)
unit.register_new(ProjectRecord("project-guid", name="Demo"))
unit.register_new(ElementRecord("project-guid", 1, "beam", cadwork_guid="…"))
unit.commit()  # atomic; parents before children

rows = ElementGateway(connection).select_for_project("project-guid")
```

## Query the normalized SQL directly

Because the store is plain, normalized SQL, you can report on it with any SQL —
no cadwork process required:

```python
connection.execute(
    "SELECT element_type, COUNT(*) FROM element GROUP BY element_type"
)
connection.execute(
    "SELECT material_name, SUM(g.volume) "
    "FROM attribute a JOIN geometry g USING (project_guid, element_id) "
    "GROUP BY material_name"
)
```

## Read typed records back — gateways & `BuildingQuery`

The end-to-end loop is **read the model → store it → query it back**. For typed
reads (frozen records, not raw tuples), go through the per-table gateways; for
the BMT structure, use the read-side `BuildingQuery` facade. Both run on a store
already filled by `pull`:

```python
from pycadwork import Document, Synchronizer
from pycadwork.persistence import BuildingQuery, open_sqlite
from pycadwork.persistence.gateways import (
    AttributeGateway, ElementGateway, GeometryGateway,
)

connection = open_sqlite(":memory:")
Synchronizer().pull(connection)          # model -> SQL
guid = Document().guid

# Per-table gateways map rows back to frozen record DTOs.
elements = ElementGateway(connection).select_for_project(guid)
geometry = {g.element_id: g for g in GeometryGateway(connection).select_for_project(guid)}
attributes = {a.element_id: a for a in AttributeGateway(connection).select_for_project(guid)}

for element in elements:
    g, a = geometry[element.id], attributes[element.id]
    print(element.id, element.element_type, a.material_name, g.length, g.volume)

# select_for_ids is the one IN-query — a given id set in a single statement.
ElementGateway(connection).select_for_ids(guid, [e.id for e in elements[:2]])
```

`BuildingQuery` answers the three BMT-structure questions directly — buildings,
the storeys under one (ascending by elevation), and the elements assigned to a
storey — each as a scoped gateway query, no whole-project load:

```python
query = BuildingQuery(connection, guid)

for building in query.buildings():                       # list[BuildingRecord]
    for storey in query.storeys(building.name):          # ascending by elevation
        elements = query.elements(building.name, storey.name)  # list[ElementRecord]
        print(building.name, storey.name, [e.id for e in elements])
```

A runnable, end-to-end version of all three (gateways, the JOIN report, and
`BuildingQuery`) lives in [`examples/persistence_queries.py`](../examples/persistence_queries.py).

## Pluggable backend

`open_sqlite` returns a `SqliteConnection`, but gateways and the unit of work
depend only on the `GatewayConnection` Protocol — `execute(sql, params)` plus a
`transaction()` context manager. Anything matching that shape (a SQLAlchemy-backed
adapter, an in-memory test double) drops in without changing a line of the
gateways, the unit of work, or the mappers.

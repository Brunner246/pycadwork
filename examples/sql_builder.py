"""Build SQL without writing SQL — the table-as-data query builder.

``pycadwork.persistence.sql`` is the one place the persistence layer assembles
SQL text. A table is modelled as *data* (:class:`Table` of :class:`Column` /
:class:`ForeignKey`), and every statement is *generated* from that model:
:func:`create_table` emits the DDL, and the fluent :class:`Insert` /
:class:`Update` / :class:`Delete` / :class:`Select` builders emit the DML. No SQL
string is written by hand — not in the schema, not in the gateways.

The builders produce SQL **text only**. Values stay caller-supplied as positional
``?`` placeholders, so the builder never interpolates a value (no injection
surface). The same ``Table`` object is the single source of truth a table is
declared with: the schema renders it to DDL and the gateways read their column /
key sets off it, so a table's shape lives in exactly one place.

    uv run python -m examples.sql_builder

The builder demos here touch no live model and run in any interpreter. The
cadwork demos at the end mirror a real model into SQL with ``Synchronizer().pull``
and then read it back with the very same builder — so those (and ``run()``)
execute inside cadwork or under the test suite's fake adapter.
"""

from __future__ import annotations

import sqlite3

from pycadwork import (
    AxisPoints,
    Beam,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
)
from pycadwork.persistence import Synchronizer, open_sqlite
from pycadwork.persistence.gateways import ElementGateway, ProjectGateway
from pycadwork.persistence.records import ElementRecord, ProjectRecord
from pycadwork.persistence.schema import ELEMENT, GEOMETRY
from pycadwork.persistence.sql import (
    Column,
    ColumnType,
    Delete,
    Insert,
    Select,
    Table,
    Update,
    create_table,
)

# One Table literal — the single source of truth for this table's shape. Note the
# three column flavours: a key column (NOT NULL, no default), columns with text /
# real defaults, and a nullable column (``not_null=False``).
TOOL = Table(
    name="tool",
    columns=(
        Column("id", ColumnType.INTEGER),
        Column("name", ColumnType.TEXT, default=""),
        Column("weight", ColumnType.REAL, default=0.0),
        Column("owner", ColumnType.TEXT, not_null=False),
    ),
    primary_key=("id",),
)

# A table whose every column is part of its key — there is nothing to update on a
# conflict, so the upsert resolves to DO NOTHING (see ``demo_build_dml``).
TAG = Table(
    name="tag",
    columns=(
        Column("tool_id", ColumnType.INTEGER),
        Column("label", ColumnType.TEXT),
    ),
    primary_key=("tool_id", "label"),
)


def demo_define_a_table_once() -> None:
    """A ``Table`` is data: it answers questions about itself, no SQL involved."""
    print("columns      =", TOOL.column_names)
    print("non-PK cols  =", TOOL.non_pk_columns())
    print("primary key  =", TOOL.primary_key)


def demo_generate_the_ddl() -> None:
    """``create_table`` renders the ``CREATE TABLE`` from the table definition."""
    print(create_table(TOOL))
    # The real schema's ``element`` table shows the harder cases the renderer
    # handles: a composite primary key, a nullable column, and a foreign key.
    print(create_table(ELEMENT))


def demo_build_dml() -> None:
    """The fluent builders emit INSERT / UPDATE / DELETE / SELECT as text."""
    # A plain insert lists every column with one placeholder each.
    print(Insert(TOOL).sql())

    # ``on_conflict_update`` makes it an idempotent upsert: on a PK conflict it
    # updates the non-key columns from the incoming row.
    print(Insert(TOOL).on_conflict_update().sql())

    # When every column is part of the key, there is nothing to update.
    print(Insert(TAG).on_conflict_update().sql())

    print(Update(TOOL).sql())
    print(Delete(TOOL).sql())

    # SELECT conditions accumulate in call order and AND-combine; ``where_in``
    # emits one placeholder per element of the set you will bind.
    print(Select(TOOL).sql())
    print(Select(TOOL).where_eq("id").sql())
    print(Select(TOOL).where_in("id", 3).sql())
    print(Select(ELEMENT).where_eq("project_guid").where_in("id", 2).sql())


def demo_round_trip_on_sqlite() -> None:
    """Generate the statements, run them on real SQLite — values stay parameters."""
    connection = sqlite3.connect(":memory:")
    connection.execute(create_table(TOOL))

    upsert = Insert(TOOL).on_conflict_update().sql()
    # The builder gives the text; the values are bound separately as ``?`` params.
    connection.execute(upsert, (1, "drill", 1.4, "alice"))
    connection.execute(upsert, (2, "saw", 3.1, None))
    # Re-inserting id 1 conflicts on the PK and updates its non-key columns.
    connection.execute(upsert, (1, "hammer", 0.9, "bob"))

    one = connection.execute(Select(TOOL).where_eq("id").sql(), (1,)).fetchall()
    print("after upsert, id 1 =", one)

    some = connection.execute(Select(TOOL).where_in("id", 2).sql(), (1, 2)).fetchall()
    print("ids in {1, 2}     =", some)


def demo_same_table_powers_the_gateways() -> None:
    """The gateway and the schema share one ``Table`` — no duplicated metadata."""
    # ``ElementGateway`` reads its columns / key off the very object the schema
    # renders to DDL: change the table once and both follow.
    assert ElementGateway.schema is ELEMENT
    print("ElementGateway.schema is the schema's ELEMENT table:", True)
    print("its columns =", ElementGateway.schema.column_names)


def demo_query_the_real_schema() -> None:
    """Drive ``connection.execute`` with a built SELECT against the real tables."""
    # ``open_sqlite`` creates the full schema (DDL also generated by the builder)
    # and runs anywhere — no live model needed. Seed two rows through the gateways
    # (themselves builder-driven); the project row comes first, as ``element`` FKs
    # to it.
    connection = open_sqlite(":memory:")
    ProjectGateway(connection).upsert(ProjectRecord("demo", name="Demo"))
    ElementGateway(connection).upsert(ElementRecord("demo", 1, "beam"))
    ElementGateway(connection).upsert(ElementRecord("demo", 2, "plate"))

    # Build the SELECT, hand its text to execute — the guid stays a ``?`` param.
    sql = Select(ELEMENT).where_eq("project_guid").sql()
    rows = connection.execute(sql, ["demo"])
    print("element rows =", rows)  # raw tuples, in ELEMENT.column_names order

    # In a live session you would fill the store from the model first —
    #     Synchronizer().pull(connection); guid = Document().guid
    # then run the very same ``Select(ELEMENT)...`` against it.

    # For typed records instead of raw tuples, prefer the gateway (same builder
    # underneath, but it maps each row back to a frozen record):
    print("as records  =", ElementGateway(connection).select_for_project("demo"))


# --- the same builder against a live cadwork model --------------------------


def _seed_model() -> None:
    """Create a small model to mirror: one beam, one plate.

    In a real project this state comes from the cadwork UI; here it is seeded
    through the public element API so the cadwork demos below have data to pull.
    """
    Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 1)),
    )
    Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


def demo_pull_then_query() -> None:
    """The real workflow: pull the model into SQL, then read it back with Select."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)  # model -> SQL, in one transaction
    guid = Document().guid

    # Every element of this project. ``.sql()`` yields the text; the guid is a
    # ``?`` param, never interpolated into the string.
    rows = connection.execute(
        Select(ELEMENT).where_eq("project_guid").sql(),
        [guid],
    )
    for row in rows:
        print("element row  =", row)  # raw tuple, in ELEMENT.column_names order

    # All geometry rows, unfiltered.
    geometry = connection.execute(Select(GEOMETRY).sql())
    print("geometry rows =", len(geometry))


def demo_filter_by_type() -> None:
    """A cadwork-flavoured query: elements of one type — two AND-combined equalities."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)
    guid = Document().guid

    # Pick a type that is actually present, then fetch just those elements.
    a_type = ElementGateway(connection).select_for_project(guid)[0].element_type
    sql = Select(ELEMENT).where_eq("project_guid", "element_type").sql()
    same_type = connection.execute(sql, [guid, a_type])
    print(f"elements of type {a_type!r} =", same_type)


def demo_typed_records_via_the_gateway() -> None:
    """For whole-row reads, prefer the gateway: frozen records, not raw tuples."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)
    guid = Document().guid

    # Same builder underneath, but each row maps back to an ``ElementRecord``.
    elements = ElementGateway(connection).select_for_project(guid)
    for element in elements:
        print(f"  {element.id}: {element.element_type}")  # typed attribute access

    # ``select_for_ids`` is the package's one IN-query — fetch a given id set.
    ids = [element.id for element in elements]
    print("first by id =", ElementGateway(connection).select_for_ids(guid, ids[:1]))


def run() -> None:
    """Run every SQL-builder demo in order."""
    # Builder fundamentals — pure string assembly, no model needed.
    demo_define_a_table_once()
    demo_generate_the_ddl()
    demo_build_dml()
    demo_round_trip_on_sqlite()
    demo_same_table_powers_the_gateways()
    demo_query_the_real_schema()
    # The same builder against a live cadwork model (mirrored into SQL first).
    _seed_model()
    demo_pull_then_query()
    demo_filter_by_type()
    demo_typed_records_via_the_gateway()


if __name__ == "__main__":
    run()

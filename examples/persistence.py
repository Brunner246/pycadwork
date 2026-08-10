"""Mirror the running model to a normalized SQL database — and back.

``pycadwork.persistence`` maps the live document into a normalized (3NF) SQLite
store and back, via two explicit operations: ``pull()`` (model -> SQL) and
``push()`` (SQL -> model). It never imports cwapi3d — it reads and writes the
model only through ``Document`` / ``Element``. The default backend is stdlib
``sqlite3``, so you can report on the store with plain SQL.

    uv run python -m examples.persistence

(Mirroring reads the live model, so this runs inside cadwork or under the test
suite's fake adapter.) All demos below are **non-destructive**: they snapshot
into an in-memory database and inspect it. (A ``push`` that rebuilds an emptied
model is shown as an idempotent no-op, so running this never deletes your model.)
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
)
from pycadwork.persistence import (
    ModelReader,
    Synchronizer,
    UnitOfWork,
    diff,
    load_snapshot,
    open_sqlite,
)
from pycadwork.persistence.records import ElementRecord, ProjectRecord


def _seed_model() -> None:
    """A small model to mirror: one beam, one plate, both given a material."""
    beam = Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 3000, 0), Point3D(0, 0, 1)),
    )
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    beam.attrs.material_name = "GL24h"
    plate.attrs.material_name = "OSB/3"


def demo_pull() -> None:
    """`pull` snapshots the model into SQL in one transaction; it is idempotent."""
    connection = open_sqlite(":memory:")  # or open_sqlite("model.db")

    report = Synchronizer().pull(connection)
    print(
        f"pull: created={report.created} updated={report.updated} "
        f"deleted={report.deleted}"
    )

    # Re-pulling an unchanged model upserts in place: no creates, all updates.
    again = Synchronizer().pull(connection)
    print(f"re-pull: created={again.created} updated={again.updated}")


def demo_query_the_sql() -> None:
    """The store is plain normalized SQL — report on it with any query."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    by_type = connection.execute(
        "SELECT element_type, COUNT(*) FROM element GROUP BY element_type"
    )
    print("elements by type =", list(by_type))

    widths = connection.execute("SELECT element_id, width FROM geometry")
    print("geometry widths =", dict(widths))


def demo_query_materials() -> None:
    """Material is normalized: a deduplicated `material` master + a per-element link.

    Every element carrying a material gets one ``element_material`` row keyed by
    its id (and carrying its cadwork GUID); the structural properties live once
    per material in ``material``. Join the two to report each element's material.
    """
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    materials = connection.execute(
        "SELECT material_name, grade, modulus_elasticity_1 FROM material"
    )
    print("material master =", list(materials))

    by_element = connection.execute(
        "SELECT em.element_id, em.cadwork_guid, m.material_name, m.weight "
        "FROM element_material em "
        "JOIN material m ON m.project_guid = em.project_guid "
        "AND m.material_name = em.material_name"
    )
    print("element -> material =", list(by_element))


def demo_read_snapshot_without_sql() -> None:
    """`ModelReader.read()` projects the model into frozen records — no SQL at all."""
    snapshot = ModelReader().read()

    for element in snapshot.elements:
        print("element", element.id, "is a", element.element_type)

    geometry = snapshot.geometry_by_element()  # dict[id, GeometryRecord]
    for element_id, record in geometry.items():
        print(f"  geom {element_id}: width={record.width} length={record.length}")


def demo_diff_before_push() -> None:
    """The diff is pure — compute what a push *would* do before doing it."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    target = load_snapshot(connection, Document().guid)  # what SQL holds
    current = ModelReader().read()  # what the model holds

    delta = diff(current, target)
    print("would create:", list(delta.new_ids))
    print("would update:", list(delta.dirty_ids))
    print("would delete:", [r.id for r in delta.removed])


def demo_push_is_a_noop_when_in_sync() -> None:
    """`push` writes SQL back into the model; with both in sync it is a safe no-op."""
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    # Every element already exists, so push only updates — nothing created/deleted.
    report = Synchronizer().push(connection)
    print(
        f"push: created={report.created} updated={report.updated} "
        f"deleted={report.deleted} skipped={report.skipped}"
    )


def demo_unit_of_work() -> None:
    """`UnitOfWork` stages records across gateways and commits them atomically.

    ``pull`` uses it under the hood; here we drive it directly. Records are
    dispatched to their table's gateway by type and written in foreign-key-safe
    order (project before element), all inside one transaction — either every
    change lands or none does.
    """
    connection = open_sqlite(":memory:")

    uow = UnitOfWork(connection)
    uow.register_new(ProjectRecord("demo", name="Demo"))
    uow.register_new(ElementRecord("demo", 1, "beam"))
    uow.register_new(ElementRecord("demo", 2, "plate"))
    uow.commit()  # one transaction; the project row lands before the elements

    count = connection.execute("SELECT COUNT(*) FROM element")
    print("after commit, element rows =", count[0][0])  # 2

    # Staged-but-not-committed changes are discarded by rollback — nothing written.
    uow.register_new(ElementRecord("demo", 3, "drilling"))
    uow.rollback()
    after = connection.execute("SELECT COUNT(*) FROM element")
    print("after rollback, element rows =", after[0][0])  # still 2


def run() -> None:
    """Run every persistence demo in order."""
    _seed_model()
    demo_pull()
    demo_query_the_sql()
    demo_query_materials()
    demo_read_snapshot_without_sql()
    demo_diff_before_push()
    demo_push_is_a_noop_when_in_sync()
    demo_unit_of_work()


if __name__ == "__main__":
    run()

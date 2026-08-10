"""Read the 3D model, store it in SQL, then query it back.

This is the capstone of the persistence story. :mod:`examples.persistence` shows
``pull`` / ``push`` / the ``UnitOfWork``, and :mod:`examples.sql_builder` shows the
table-as-data builder; here we focus on the **read side** — once the model is
mirrored into SQL, how do you get data *out*?

Three answers, in rising order of structure:

* **Gateways** — one per table, each mapping rows back to frozen record DTOs
  (``ElementGateway``, ``GeometryGateway``, ``AttributeGateway``).
* **Plain SQL** — the store is normalized 3NF, so a JOIN across the satellites
  reports across the whole model with no cadwork involved.
* **``BuildingQuery``** — the read-side navigation facade: building → storeys →
  elements, each call a scoped gateway query.

    uv run python -m examples.persistence_queries

Reading the live model needs a backend, so ``run()`` executes inside cadwork or
under the test suite's fake adapter. Every demo is non-destructive: it snapshots
into an in-memory database and reads it.
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    BuildingName,
    Document,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    StoreyAssigner,
)

# Seam access — only to seed the building's BMT storeys (mimics the cadwork UI).
from pycadwork.cadwork_adapter import cadwork
from pycadwork.persistence import BuildingQuery, Synchronizer, open_sqlite
from pycadwork.persistence.gateways import (
    AttributeGateway,
    ElementGateway,
    GeometryGateway,
)

_BUILDING = "Building A"


def _beam_z(z_lo: float, z_hi: float, material: str) -> Beam:
    """A vertical beam spanning ``[z_lo, z_hi]``, tagged with a material."""
    beam = Beam.create_rectangular(
        RectSection(80.0, z_hi - z_lo),
        AxisPoints(
            Point3D(0.0, 0.0, z_lo),
            Point3D(0.0, 1000.0, z_lo),
            Point3D(0.0, 0.0, z_lo + 1.0),
        ),
    )
    beam.attrs.material_name = material
    return beam


def _seed_model() -> None:
    """A small framed model with materials and BMT storeys.

    In a real project this state is authored in cadwork; here it is seeded
    through the public API (and, for the storeys, the version-isolation seam) so
    the read → store → query demos have something to work on.
    """
    # Three storeys for the building (mimics the cadwork BMT structure).
    cadwork.bim.set_storey_height(_BUILDING, "S0", 0.0)
    cadwork.bim.set_storey_height(_BUILDING, "S1", 3000.0)
    cadwork.bim.set_storey_height(_BUILDING, "S2", 6000.0)

    # Two ground-floor posts, a first-floor beam, and a panel — varied materials.
    post_a = _beam_z(0.0, 2900.0, "Pine")
    post_b = _beam_z(0.0, 2900.0, "Pine")
    beam = _beam_z(3000.0, 3200.0, "Spruce")
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 100), Point3D(2400, 0, 100), Point3D(0, 0, 101)),
    )
    plate.attrs.material_name = "OSB"

    # Classify them into the building's storeys (writes building/storey back to
    # the model, so a later ``pull`` captures the assignments).
    StoreyAssigner(BuildingName(_BUILDING)).assign([post_a, post_b, beam, plate])


def demo_read_then_store() -> None:
    """The core loop: read the live model, write it into SQL in one transaction."""
    connection = open_sqlite(":memory:")  # or open_sqlite("model.db") for a file

    report = Synchronizer().pull(connection)  # model -> SQL, atomic
    print(
        f"pull: created={report.created} updated={report.updated} "
        f"deleted={report.deleted}"
    )

    # The store is now a normalized mirror — count what landed, per table.
    for table in ("element", "geometry", "attribute", "storey_assignment"):
        count = connection.execute(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table}: {count[0][0]} rows")


def demo_query_with_gateways() -> None:
    """Read typed records back through the per-table gateways.

    Each gateway maps its table's rows to frozen record DTOs (not raw tuples).
    The 1:1 satellites — geometry, attributes — are indexed by element id and
    joined in Python, mirroring the normalized shape.
    """
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)
    guid = Document().guid

    elements = ElementGateway(connection).select_for_project(guid)
    geometry = {
        g.element_id: g for g in GeometryGateway(connection).select_for_project(guid)
    }
    attributes = {
        a.element_id: a for a in AttributeGateway(connection).select_for_project(guid)
    }

    for element in elements:
        g = geometry[element.id]
        a = attributes[element.id]
        print(
            f"  #{element.id} {element.element_type:<6} "
            f"{a.material_name or '-':<7} length={g.length:.0f} volume={g.volume:.4g}"
        )

    # ``select_for_ids`` is the package's one IN-query — fetch a given id set in a
    # single statement instead of one round-trip per id.
    ids = [element.id for element in elements[:2]]
    picked = ElementGateway(connection).select_for_ids(guid, ids)
    print("by id set =", [element.id for element in picked])


def demo_report_with_sql_join() -> None:
    """A cross-table report: total volume per material, in one SQL JOIN.

    The store is plain normalized SQL, so a JOIN across the ``attribute`` and
    ``geometry`` satellites (both keyed by ``(project_guid, element_id)``)
    aggregates across the whole model with no cadwork involved.
    """
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)

    rows = connection.execute(
        "SELECT a.material_name, COUNT(*) AS n, SUM(g.volume) AS total_volume "
        "FROM attribute a "
        "JOIN geometry g USING (project_guid, element_id) "
        "GROUP BY a.material_name "
        "ORDER BY total_volume DESC"
    )
    for material, n, total in rows:
        print(f"  {material or '(none)':<8} count={n} total_volume={total:.4g}")


def demo_navigate_with_building_query() -> None:
    """``BuildingQuery`` — the read-side facade over building → storeys → elements.

    Where the gateways are per-table, ``BuildingQuery`` answers the three
    BMT-structure questions directly: which buildings exist, which storeys sit
    under one (ascending by elevation), and which elements were assigned to a
    storey. Each call is a scoped gateway query — no whole-project load.
    """
    connection = open_sqlite(":memory:")
    Synchronizer().pull(connection)
    guid = Document().guid

    query = BuildingQuery(connection, guid)

    for building in query.buildings():
        print("building:", building.name)
        for storey in query.storeys(building.name):  # ascending by elevation
            elements = query.elements(building.name, storey.name)
            ids = [element.id for element in elements]
            print(f"  {storey.name} (z={storey.elevation:.0f}) -> elements {ids}")


def run() -> None:
    """Run every read → store → query demo in order."""
    _seed_model()
    demo_read_then_store()
    demo_query_with_gateways()
    demo_report_with_sql_join()
    demo_navigate_with_building_query()


if __name__ == "__main__":
    run()

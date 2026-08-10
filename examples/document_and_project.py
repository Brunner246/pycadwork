"""The Document repository and the ProjectInfo metadata view.

``Document`` is the top-level handle for the active project. It does two jobs:
it **is the element repository** (a live view over the whole model) and it
**manages the project** through its ``project`` component. Construction takes no
arguments — there is exactly one active project.

    uv run python -m examples.document_and_project
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


def _seed_some_elements() -> None:
    """Put a couple of elements in the model so the repository has something to list."""
    Beam.create_rectangular(
        RectSection(120, 240),
        AxisPoints(Point3D(0, 0, 0), Point3D(3000, 0, 0), Point3D(0, 0, 1)),
    )
    Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )


def demo_repository() -> None:
    """The repository methods are live queries, wrapped to their typed classes."""
    doc = Document()

    every = doc.elements()  # list[Element], every identifiable element
    print("total elements =", len(every))

    # Narrow by runtime type — no per-type accessor exists, this subsumes them all.
    beams = doc.elements_of(Beam)  # list[Beam]
    plates = doc.elements_of(Plate)  # list[Plate]
    print("beams =", len(beams), "plates =", len(plates))

    # `active()` is the current selection; in a fresh model it mirrors everything.
    print("active =", len(doc.active()))

    if beams:
        # `get(id)` wraps a single id (delegates to from_id).
        one = doc.get(beams[0].id)
        print("get(first beam) ->", type(one).__name__)

    # `covers()` discovers every Wall / Slab / Roof aggregate (none here yet).
    print("covers =", len(doc.covers()))


def demo_project_metadata() -> None:
    """ProjectInfo mirrors Element.attrs: reads are properties, writes are set_*."""
    project = Document().project

    project.set_name("Cabin A")
    project.set_number("2026-014")
    project.set_architect("M. Brunner")
    project.set_customer("Alpine Builders")
    project.set_designer("Studio North")
    project.set_latitude(47.05)
    project.set_longitude(8.31)

    print("name      =", project.name)
    print("number    =", project.number)
    print("architect =", project.architect)
    print("customer  =", project.customer)
    print("designer  =", project.designer)
    print("lat/lon   =", project.latitude, project.longitude)
    print("guid      =", project.guid)  # read-only in cwapi3d

    # The GUID is read-only, but you can mint a fresh one when you need a new id.
    print("new guid  =", project.new_guid())


def demo_delete_elements() -> None:
    """`Document.delete` removes elements from the model in one batched call."""
    doc = Document()
    before = len(doc.elements())

    # A throwaway beam, then delete it — the repository count drops back.
    scratch = Beam.create_rectangular(
        RectSection(60, 120),
        AxisPoints(Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 0, 1)),
    )
    print("after create =", len(doc.elements()))  # before + 1

    Document.delete([scratch])
    print("after delete =", len(doc.elements()))  # back to `before`
    assert len(doc.elements()) == before


def demo_project_data_store() -> None:
    """Indexed user-attributes and a free-form key/value project-data store."""
    project = Document().project

    project.set_user_attribute(1, "phase-1")
    print("project user_attribute(1) =", project.user_attribute(1))

    project.set_data("revision", "C")
    project.set_data("checked-by", "team-2")
    print("data keys =", sorted(project.data_keys()))
    print("revision  =", project.data("revision"))


def run() -> None:
    """Run every document/project demo in order."""
    _seed_some_elements()
    demo_repository()
    demo_project_metadata()
    demo_delete_elements()
    demo_project_data_store()


if __name__ == "__main__":
    run()

"""Typed elements — create them, read their attributes and geometry, write back.

Every wrapper (``Beam``, ``Plate``, ``Drilling``, …) is a *live view* over a
cadwork element id: reads query the model at call time, and the matching setter
property writes straight back. Each element aggregates two small component
views — ``element.attrs`` and ``element.geometry``.

    uv run python -m examples.elements

(Creating elements needs a backend: this runs fully inside cadwork or under the
test suite's fake adapter.)
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    CrossSection,
    Drilling,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Segment,
    from_id,
)


def demo_create_a_beam() -> Beam:
    """Create a 120x240 rectangular beam 3 m long and report its geometry."""
    beam = Beam.create_rectangular(
        RectSection(width=120.0, height=240.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(3000, 0, 0), Point3D(0, 0, 1)),
    )
    print("created", beam)  # Beam(id=..., name='')
    print("length =", beam.geometry.length)  # 3000.0
    print("width  =", beam.geometry.width)  # 120.0
    print("cross-section =", beam.cross_section)  # CrossSection.RECTANGULAR
    assert beam.cross_section is CrossSection.RECTANGULAR
    return beam


def demo_read_and_write_attributes(beam: Beam) -> None:
    """attrs are symmetric: reading a property and assigning it both hit the model."""
    beam.attrs.name = "Stud-01"
    beam.attrs.group = "frame"
    beam.attrs.material_name = "Pine"
    beam.attrs.comment = "load-bearing"

    print("name     =", beam.attrs.name)
    print("group    =", beam.attrs.group)
    print("material =", beam.attrs.material_name)

    # Indexed user attributes stay methods (they can't be a bare property).
    beam.attrs.set_user_attribute(1, "phase-1")
    print("user_attribute(1) =", beam.attrs.user_attribute(1))


def demo_write_back_dimensions(beam: Beam) -> None:
    """Assigning a geometry dimension writes the real size back to the model."""
    print("width before =", beam.geometry.width)
    beam.geometry.width = 100.0  # writes through to the backend
    print("width after  =", beam.geometry.width)  # 100.0
    print("center of gravity =", beam.geometry.center_of_gravity)


def demo_create_a_plate() -> Plate:
    """A Plate is panel-like: its geometry adds a ``thickness`` alias for height."""
    plate = Plate.create_rectangular(
        PanelSection(width=600.0, thickness=18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    print("created", plate)
    print("thickness =", plate.geometry.thickness)  # 18.0
    return plate


def demo_create_a_drilling() -> Drilling:
    """A Drilling is an axis defined by a diameter and a two-point Segment."""
    drilling = Drilling.create(
        diameter=12.0,
        axis=Segment(Point3D(0, 0, 0), Point3D(0, 0, 200)),
    )
    print("created", drilling, "length", drilling.geometry.length)
    return drilling


def demo_wrap_existing_id(beam: Beam) -> None:
    """`from_id` wraps an existing id in its most specific subclass."""
    same = from_id(beam.id)
    print("from_id ->", type(same).__name__, "id", same.id)  # Beam
    assert isinstance(same, Beam)
    assert same == beam  # equality is by (type, id)


def run() -> None:
    """Run every element demo in order."""
    beam = demo_create_a_beam()
    demo_read_and_write_attributes(beam)
    demo_write_back_dimensions(beam)
    demo_create_a_plate()
    demo_create_a_drilling()
    demo_wrap_existing_id(beam)


if __name__ == "__main__":
    run()

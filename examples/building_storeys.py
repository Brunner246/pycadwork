"""Classify elements into a building's storeys by their vertical extent.

The pure core, :class:`StoreyStack`, partitions the vertical axis into half-open
intervals and reports the majority storey for any extent — no cadwork involved,
so it is plain testable geometry. :class:`StoreyAssigner` wraps that with the
real model: it reads a building's BMT storeys, classifies each element's AABB,
writes the building/storey back, and *marks* straddling elements for review.

    uv run python -m examples.building_storeys

.. note::

   In a real project the BMT storeys already exist (created in cadwork). To stay
   runnable standalone, ``demo_storey_assigner`` seeds three storeys through the
   version-isolation seam — that mimics the BMT structure; it is setup, not part
   of normal pycadwork usage.
"""

from __future__ import annotations

from pycadwork import (
    AxisPoints,
    Beam,
    BuildingName,
    Point3D,
    RectSection,
    Storey,
    StoreyName,
    StoreyStack,
    StoreyAssigner,
)

# Seam access — only to seed the building's storeys (mimics the BMT structure).
from pycadwork.cadwork_adapter import cadwork

_BUILDING = "Building A"


def demo_storey_stack_pure() -> None:
    """The classifier on its own — pure geometry, no model needed."""
    stack = StoreyStack(
        [
            Storey(StoreyName("GF"), elevation=0.0),
            Storey(StoreyName("1F"), elevation=3000.0),
            Storey(StoreyName("2F"), elevation=6000.0),
        ]
    )

    # An extent that sits cleanly inside the ground floor.
    clean = stack.classify(z_lo=100.0, z_hi=2800.0)
    print("GF extent ->", clean.storey.name.value, "spans?", clean.spans)  # GF, False

    # An extent that crosses the GF/1F plane: assigned to the majority storey,
    # and flagged as spanning so a human can review it.
    crossing = stack.classify(z_lo=2900.0, z_hi=3300.0)
    print(
        "crossing ->", crossing.storey.name.value, "spans?", crossing.spans
    )  # 1F, True


def _beam_z(z_lo: float, z_hi: float) -> Beam:
    """A beam whose AABB spans ``[z_lo, z_hi]`` vertically."""
    return Beam.create_rectangular(
        RectSection(80.0, z_hi - z_lo),
        AxisPoints(
            Point3D(0.0, 0.0, z_lo),
            Point3D(0.0, 1000.0, z_lo),
            Point3D(0.0, 0.0, z_lo + 1.0),
        ),
    )


def _seed_storeys() -> None:
    """Register three storeys for the building (mimics the BMT structure)."""
    cadwork.bim.set_storey_height(_BUILDING, "S0", 0.0)
    cadwork.bim.set_storey_height(_BUILDING, "S1", 3000.0)
    cadwork.bim.set_storey_height(_BUILDING, "S2", 6000.0)


def demo_storey_assigner() -> None:
    """Assign real elements to storeys and read back the report."""
    _seed_storeys()

    ground = _beam_z(100.0, 2900.0)  # clean S0
    first = _beam_z(3100.0, 3500.0)  # clean S1
    spanning = _beam_z(2900.0, 3300.0)  # crosses S0/S1 -> majority S1, marked

    report = StoreyAssigner(BuildingName(_BUILDING)).assign([ground, first, spanning])
    for assignment in report:
        print(
            f"element {assignment.element.id} -> {assignment.storey.name.value} "
            f"(spans={assignment.spans})"
        )

    # The straddling element was marked in the default user-attribute slot (1).
    print("spanning element's marker =", spanning.attrs.user_attribute(1))


def run() -> None:
    """Run every building/storey demo in order."""
    demo_storey_stack_pure()
    demo_storey_assigner()


if __name__ == "__main__":
    run()

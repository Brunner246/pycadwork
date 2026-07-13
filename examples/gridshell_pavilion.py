"""Build a timber gridshell pavilion from a doubly-curved surface.

Recreates the shape of a canopy gridshell like the "gravitational pavilion"
(https://www.miro.vision/index.php/2021/01/14/gravitaional-pavilion/): a smooth
doubly-curved surface that rises to a peak and meets the ground at its
perimeter, realized either as a lattice of mitered ribs (``members``) or as a
closed shell of panels (``panels``).

The pipeline starts with :class:`TriangulatedSurfaceBuilder`, which samples a
parametric canopy ``f(u, v)`` into a triangle mesh (one planar ``Surface`` per
triangle, nurbs-style). :class:`GridShellBuilder` then realises it, and the hard
part — the high-valence interior nodes where five or six ribs meet — is solved by
a pluggable joint strategy passed to :meth:`~GridShellBuilder.joint`. This example
builds the same canopy every way so they stand side by side in cadwork:

* :class:`HubConnectorJoint` — set the ribs back and fill the node void with a
  standard connector plus dowels.
* :class:`RadialMiterJoint` — cut every rib on the angular-bisector planes so the
  rosette butts on shared faces, no void.
* :class:`LapJoint` — housed cross-laps with bolts at the through-nodes.
* ``.laths(...)`` — the authentic strained gridshell: two families of continuous
  laths layered along the normal and bolted at crossings, so no hub joint arises.
* ``.panels(...)`` — the same canopy as a closed shell of flat panels.

Run it standalone against the in-memory fake, or from cadwork's Python API menu
to see the real solids::

    uv run python -m examples.gridshell_pavilion

.. note::

   Raise :data:`DIVISIONS` for a finer, more sculptural shell (more ribs), and
   swap :func:`_canopy` for any ``f(u, v)`` to change the form. Each demo builds
   its canopy at a different plan location so they are visible side by side.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from pycadwork import DisplayRefreshScope, Point3D, RectSection
from pycadwork.gridshell import (
    GridShellBuilder,
    HubConnectorJoint,
    LapJoint,
    RadialMiterJoint,
    TriangulatedSurfaceBuilder,
)

# ---- pavilion parameters (cadwork works in millimetres) ----
SPAN_X = 8000.0  #: plan footprint along X
SPAN_Y = 8000.0  #: plan footprint along Y
HEIGHT = 3200.0  #: peak rise of the canopy
DIVISIONS = 8  #: grid cells per side; raise for a finer shell
RIB = RectSection(60.0, 220.0)  #: rib cross-section (width x height)
PANEL_THICKNESS = 40.0  #: panel shell thickness


def _canopy(
    origin_x: float = 0.0, origin_y: float = 0.0
) -> Callable[[float, float], Point3D]:
    """A doubly-curved canopy: peaks in the centre, drops to zero at the edges.

    ``u`` and ``v`` sweep [0, 1] over the plan footprint; the sine-product
    height field gives the smooth, ground-meeting shell of a gridshell canopy.
    """

    def f(u: float, v: float) -> Point3D:
        x = origin_x + u * SPAN_X
        y = origin_y + v * SPAN_Y
        z = HEIGHT * math.sin(math.pi * u) * math.sin(math.pi * v)
        return Point3D(x, y, z)

    return f


def _build_canopy_surfaces(origin_x: float = 0.0, origin_y: float = 0.0):
    """Sample the canopy into a triangulated surface (one Surface per triangle)."""
    return (
        TriangulatedSurfaceBuilder()
        .from_function(_canopy(origin_x, origin_y), DIVISIONS, DIVISIONS)
        .build()
    )


def _canopy_grid(origin_x: float = 0.0, origin_y: float = 0.0):
    """Sample the canopy into a raw (rows x cols) grid — the input a lath build needs."""
    f = _canopy(origin_x, origin_y)
    return [
        [f(i / DIVISIONS, j / DIVISIONS) for j in range(DIVISIONS + 1)]
        for i in range(DIVISIONS + 1)
    ]


def demo_triangulated_surface() -> None:
    """Step 1: turn a parametric canopy into a triangle mesh."""
    surfaces = _build_canopy_surfaces()
    print("triangulated surface:", len(surfaces), "triangles")


def demo_hub_connector_gridshell() -> None:
    """Step 2a: rib lattice with hub-connector nodes.

    Each rib is set back from every multi-rib node (a section-derived gap, so it
    need not be hand-tuned), the void is filled with a standard connector, and a
    dowel is drilled down each rib into it. Genuine two-rib corners still miter.
    This is the ``.joint(...)`` entry point replacing the old bare setback.
    """
    surfaces = _build_canopy_surfaces()
    with DisplayRefreshScope():
        result = (
            GridShellBuilder(surfaces)
            .members(RIB)
            .joint(HubConnectorJoint(connector_name="BSB-hub", dowel_diameter=12.0))
            .build()
        )
    print(
        "hub-connector gridshell:",
        len(result.members),
        "ribs,",
        len(result.connectors),
        "connectors,",
        len(result.drillings),
        "dowels",
    )
    for warning in result.warnings:
        print("  warning:", warning)


def demo_radial_miter_gridshell() -> None:
    """Step 2b: rib lattice with radial (multi-rib) miters.

    Every rib at a node is cut on the angular-bisector planes between it and its
    neighbours, so the whole rosette butts on shared faces with no void and no
    connector. Offset in +X so it sits beside the hub-connector shell in cadwork.
    """
    surfaces = _build_canopy_surfaces(origin_x=SPAN_X + 2000.0)
    with DisplayRefreshScope():
        result = (
            GridShellBuilder(surfaces).members(RIB).joint(RadialMiterJoint()).build()
        )
    print("radial-miter gridshell:", len(result.members), "ribs")
    for warning in result.warnings:
        print("  warning:", warning)


def demo_lap_joint_gridshell() -> None:
    """Step 2c: rib lattice with housed cross-laps + bolts at the through-nodes."""
    surfaces = _build_canopy_surfaces(origin_x=2 * (SPAN_X + 2000.0))
    with DisplayRefreshScope():
        result = (
            GridShellBuilder(surfaces)
            .members(RIB)
            .joint(LapJoint(bolt_count=1, bolt_diameter=12.0))
            .build()
        )
    print("lap-joint gridshell:", len(result.members), "ribs")
    for warning in result.warnings:
        print("  warning:", warning)


def demo_double_layer_lath_shell() -> None:
    """Step 2d: the strained-gridshell double layer of continuous laths.

    Two families of laths (rows and columns) are stacked along the shell normal
    and bolted at every crossing; the laths run straight through the interior
    nodes, so no multi-rib hub joint is ever needed. Offset in +Y.
    """
    grid = _canopy_grid(origin_y=SPAN_Y + 2000.0)
    with DisplayRefreshScope():
        result = (
            GridShellBuilder.from_grid(grid)
            .laths(RIB, layer_gap=RIB.height, bolt_diameter=12.0)
            .build()
        )
    print(
        "double-layer lath shell:",
        len(result.laths),
        "laths,",
        len(result.drillings),
        "bolts",
    )
    for warning in result.warnings:
        print("  warning:", warning)


def demo_panel_shell() -> None:
    """Step 2e: build the same canopy as a closed shell of panels.

    Offset in +Y (second row) so it sits clear of the rib lattices and laths.
    """
    surfaces = _build_canopy_surfaces(origin_y=2 * (SPAN_Y + 2000.0))
    with DisplayRefreshScope():
        result = GridShellBuilder(surfaces).panels(PANEL_THICKNESS).build()
    print("panel shell:", len(result.panels), "panels")
    for warning in result.warnings:
        print("  warning:", warning)


def run() -> None:
    """Build the canopy every way: three jointed rib lattices, laths, and panels."""
    demo_triangulated_surface()
    demo_hub_connector_gridshell()
    demo_radial_miter_gridshell()
    demo_lap_joint_gridshell()
    demo_double_layer_lath_shell()
    demo_panel_shell()


if __name__ == "__main__":
    run()

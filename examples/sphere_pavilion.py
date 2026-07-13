"""Build a geodesic timber sphere pavilion — frame + cladding, standing on the ground.

A sphere pavilion is a timber geodesic dome: a triangulated sphere whose struts
are as close to one length as the geometry allows, whose 5–6-strut nodes are
resolved with **radial bisector "shift cuts"** (every strut trimmed on its
neighbours' bisector planes so the rosette butts on shared flat faces), which is
**truncated by a horizontal plane** so it stands flat on the ground, and which is
**clad** with triangular panels leaving a uniform open joint on every side.

The pipeline reuses the gridshell realization stack — a geodesic icosphere is
just another triangle soup — and adds the sphere-specific parts:
:func:`~pycadwork.sphere.icosphere.icosphere_faces` (subdivide an icosahedron and
project to the radius), a flat ground cut, gapped cladding, and a strut schedule
that bins the members into the few length classes a shop actually cuts.

Run it standalone against the in-memory fake, or from cadwork's Python API menu
to see the real solids::

    uv run python -m examples.sphere_pavilion

.. note::

   Raise :data:`FREQUENCY` for a finer sphere (more, shorter struts and more
   length classes); frequency 1 is the raw icosahedron, where all 30 struts are
   genuinely identical.
"""

from __future__ import annotations

from pycadwork import DisplayRefreshScope, Point3D, RectSection
from pycadwork.sphere import (
    SpherePavilionBuilder,
    faces_to_surfaces,
    icosphere_faces,
)

# ---- pavilion parameters (cadwork works in millimetres) ----
RADIUS = 4000.0  #: sphere radius
FREQUENCY = 3  #: icosahedron subdivision level; raise for a finer sphere
GROUND_CUT = 1500.0  #: horizontal cut this far below the centre (stands flat)
TIMBER = RectSection(60.0, 120.0)  #: strut cross-section (width x height)
SILL = RectSection(120.0, 160.0)  #: base sill-ring cross-section (heavier band)
CLADDING_THICKNESS = 27.0  #: cladding panel thickness
CLADDING_GAP = 15.0  #: uniform open joint between adjacent panels
FOUNDATION_THICKNESS = 300.0  #: concrete slab thickness under the base

#: Centre-to-centre spacing so the three demos stand side by side in +Y with a
#: 2000 mm clear gap between neighbouring spheres (each is ``2 * RADIUS`` across).
Y_SPACING = 2.0 * RADIUS + 2000.0


def demo_geodesic_mesh(y_offset: float = 0.0) -> None:
    """Step 1: subdivide an icosahedron into cadwork surfaces on the sphere.

    ``icosphere_faces`` is pure geometry (a list of point triangles) and creates
    nothing in the model; ``faces_to_surfaces`` is what actually builds one
    cadwork ``Surface`` per triangle — that is what you see in the 3D view.
    """
    faces = icosphere_faces(RADIUS, FREQUENCY, Point3D(0.0, y_offset, GROUND_CUT))
    with DisplayRefreshScope() as scope:
        surfaces = faces_to_surfaces(faces)
        scope.track(surfaces)
    print("geodesic mesh:", len(surfaces), "surfaces at frequency", FREQUENCY)


def demo_full_sphere_frame(y_offset: float = 0.0) -> None:
    """Step 2: the whole sphere as a strut frame with radial bisector nodes."""
    with DisplayRefreshScope() as scope:
        result = (
            SpherePavilionBuilder(RADIUS)
            .frequency(FREQUENCY)
            .center(Point3D(0.0, y_offset, 0.0))
            .timber(TIMBER)
            .build()
        )
        # Repaint the struts once, on scope exit, instead of after every create.
        scope.track(result.members)
    print("full sphere frame:", len(result.members), "struts")
    _print_strut_schedule(result.strut_groups)


def demo_dome_with_cladding(y_offset: float = 0.0) -> None:
    """Step 3: cut to a dome on a clean sill ring + slab, clad with gapped panels."""
    with DisplayRefreshScope() as scope:
        result = (
            SpherePavilionBuilder(RADIUS)
            .frequency(FREQUENCY)
            .center(Point3D(0.0, y_offset, 0.0))  # place in plan; base lands on z=0
            .ground_cut(GROUND_CUT)
            .timber(TIMBER)
            .sill(SILL)
            .cladding(thickness=CLADDING_THICKNESS, gap=CLADDING_GAP)
            .foundation(FOUNDATION_THICKNESS, material="C25/30")
            .build()
        )
        # Everything was created with refresh suspended, so recreate together.
        elements = [*result.members, *result.panels, *result.ring]
        if result.foundation is not None:
            elements.append(result.foundation)
        scope.track(elements)
    print(
        "ground-cut dome:",
        len(result.members),
        "struts,",
        len(result.ring),
        "sill-ring beams,",
        len(result.panels),
        "cladding panels,",
        "foundation" if result.foundation is not None else "no foundation",
    )
    _print_strut_schedule(result.strut_groups)
    for warning in result.warnings:
        print("  warning:", warning)


def _print_strut_schedule(groups) -> None:
    """Print the length classes the members fall into (the fabrication schedule)."""
    for label, group in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", groups):
        print(f"  strut {label}: {group.nominal_length:.0f} mm x {group.count}")


def run() -> None:
    """Build all three side by side in +Y with a 2000 mm gap between them."""
    demo_geodesic_mesh(0.0 * Y_SPACING)
    demo_full_sphere_frame(1.0 * Y_SPACING)
    demo_dome_with_cladding(2.0 * Y_SPACING)


if __name__ == "__main__":
    run()

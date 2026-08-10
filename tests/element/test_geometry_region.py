"""``geometry.bounding_region`` reports each element's tightest native region:
a frame-aligned OBB for axis-anchored elements, a world-aligned AABB for the
rest. The choice is made by the geometry-component hierarchy (inheritance),
not by branching on the element type at the call site.
"""

from __future__ import annotations

from pycadwork import AxisPoints, Beam, Node, Point3D, RectSection
from pycadwork.geometry import AxisAlignedBoundingBox, OrientedBoundingBox


def test_linear_element_bounding_region_is_oriented():
    beam = Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    region = beam.geometry.bounding_region
    assert isinstance(region, OrientedBoundingBox)
    # It is the tight frame OBB, not a re-derivation.
    assert region == beam.geometry.obb


def test_non_linear_element_bounding_region_is_axis_aligned():
    node = Node.create(Point3D(10.0, 20.0, 30.0))
    region = node.geometry.bounding_region
    assert isinstance(region, AxisAlignedBoundingBox)
    assert region == node.geometry.aabb

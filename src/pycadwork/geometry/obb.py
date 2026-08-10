from __future__ import annotations

from collections.abc import Iterable

from pycadwork.geometry.aabb import AxisAlignedBoundingBox
from pycadwork.geometry.frame3d import Frame3D
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D

_SAT_PARALLEL_EPSILON = 1e-10


class OrientedBoundingBox:
    """An oriented (non-axis-aligned) bounding box in 3D space.

    Defined by a :class:`Frame3D` -- whose origin is the box center and whose
    orthonormal axes are the box's local axes -- together with three
    non-negative half-extents giving the box's reach along each local axis.

    Use this for bounding objects whose natural orientation differs from the
    world axes (rotated CAD elements, beams, ...). For world-aligned bounding
    regions, use :class:`AxisAlignedBoundingBox`.
    """

    __slots__ = ("_frame", "_half_extents")

    def __init__(self, points: Iterable[Point3D], frame: Frame3D) -> None:
        """Build the tight OBB aligned to *frame*'s axes from *points*.

        Each point is projected into the input frame's local space; the per-axis
        local extrema yield the half-extents, and the world-space midpoint of
        those extrema becomes the OBB center. The input frame's axes are
        preserved; only its origin is replaced.

        Raises:
            ValueError: if *points* is empty.
        """
        iterator = iter(points)
        try:
            first = next(iterator)
        except StopIteration as exc:
            raise ValueError("OrientedBoundingBox requires at least one point") from exc

        local_first = frame.world_to_local(first)
        xmin = xmax = local_first.x
        ymin = ymax = local_first.y
        zmin = zmax = local_first.z

        for p in iterator:
            lp = frame.world_to_local(p)
            if lp.x < xmin:
                xmin = lp.x
            elif lp.x > xmax:
                xmax = lp.x
            if lp.y < ymin:
                ymin = lp.y
            elif lp.y > ymax:
                ymax = lp.y
            if lp.z < zmin:
                zmin = lp.z
            elif lp.z > zmax:
                zmax = lp.z

        local_center = Point3D(
            0.5 * (xmin + xmax),
            0.5 * (ymin + ymax),
            0.5 * (zmin + zmax),
        )
        world_center = frame.local_to_world(local_center)

        self._frame = Frame3D(world_center, frame.axis_x, frame.axis_y, frame.axis_z)
        self._half_extents = Vector3D(
            0.5 * (xmax - xmin),
            0.5 * (ymax - ymin),
            0.5 * (zmax - zmin),
        )

    # ------------------------------------------------------------------
    # Static factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def from_frame_and_half_extents(
        frame: Frame3D, half_extents: Vector3D
    ) -> OrientedBoundingBox:
        """Build an OBB directly from a centered frame and half-extents.

        The frame's origin is taken as the box center; its axes define the
        local orientation.

        Raises:
            ValueError: if any half-extent is negative.
        """
        if half_extents.x < 0.0 or half_extents.y < 0.0 or half_extents.z < 0.0:
            raise ValueError(
                "from_frame_and_half_extents: half-extents must be non-negative"
            )

        box = OrientedBoundingBox.__new__(OrientedBoundingBox)
        box._frame = Frame3D(frame.origin, frame.axis_x, frame.axis_y, frame.axis_z)
        box._half_extents = Vector3D(half_extents.x, half_extents.y, half_extents.z)
        return box

    @staticmethod
    def from_axis_aligned(aabb: AxisAlignedBoundingBox) -> OrientedBoundingBox:
        """Lift an :class:`AxisAlignedBoundingBox` into an OBB on the world axes.

        The result is the same region expressed in OBB form: centered on the
        AABB's center, oriented to the world axes, with half-extents equal to
        half the AABB's size. Lets code that works in OBB space (the SAT
        intersection test) handle AABB-only inputs through one path.
        """
        size = aabb.size
        return OrientedBoundingBox.from_frame_and_half_extents(
            Frame3D(
                aabb.center,
                Vector3D(1.0, 0.0, 0.0),
                Vector3D(0.0, 1.0, 0.0),
                Vector3D(0.0, 0.0, 1.0),
            ),
            Vector3D(0.5 * size.x, 0.5 * size.y, 0.5 * size.z),
        )

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def frame(self) -> Frame3D:
        return Frame3D(
            self._frame.origin,
            self._frame.axis_x,
            self._frame.axis_y,
            self._frame.axis_z,
        )

    @property
    def center(self) -> Point3D:
        o = self._frame.origin
        return Point3D(o.x, o.y, o.z)

    @property
    def axis_x(self) -> Vector3D:
        a = self._frame.axis_x
        return Vector3D(a.x, a.y, a.z)

    @property
    def axis_y(self) -> Vector3D:
        a = self._frame.axis_y
        return Vector3D(a.x, a.y, a.z)

    @property
    def axis_z(self) -> Vector3D:
        a = self._frame.axis_z
        return Vector3D(a.x, a.y, a.z)

    @property
    def half_extents(self) -> Vector3D:
        h = self._half_extents
        return Vector3D(h.x, h.y, h.z)

    @property
    def size(self) -> Vector3D:
        h = self._half_extents
        return Vector3D(2.0 * h.x, 2.0 * h.y, 2.0 * h.z)

    def corners(self) -> list[Point3D]:
        """Return the 8 corner vertices of the box in world coordinates."""
        h = self._half_extents
        result: list[Point3D] = []
        for sx in (-1.0, 1.0):
            for sy in (-1.0, 1.0):
                for sz in (-1.0, 1.0):
                    local = Point3D(sx * h.x, sy * h.y, sz * h.z)
                    result.append(self._frame.local_to_world(local))
        return result

    def is_empty(self) -> bool:
        """True if the box has no volume on at least one axis."""
        h = self._half_extents
        return h.x <= 0.0 or h.y <= 0.0 or h.z <= 0.0

    # ------------------------------------------------------------------
    # Predicates
    # ------------------------------------------------------------------

    def contains_point(self, p: Point3D) -> bool:
        local = self._frame.world_to_local(p)
        h = self._half_extents
        return (
            -h.x <= local.x <= h.x and -h.y <= local.y <= h.y and -h.z <= local.z <= h.z
        )

    def intersects(self, other: OrientedBoundingBox) -> bool:
        """Test OBB-OBB intersection via the separating axis theorem."""
        return _obb_obb_sat(self, other)

    # ------------------------------------------------------------------
    # Conversion
    # ------------------------------------------------------------------

    def to_axis_aligned_bounding_box(self) -> AxisAlignedBoundingBox:
        """Return the world-aligned AABB enclosing this OBB."""
        return AxisAlignedBoundingBox(self.corners())

    def expanded(self, margin: float) -> OrientedBoundingBox:
        """Return a copy grown by ``margin`` along each local axis.

        Orientation and center are unchanged; each half-extent grows by
        ``margin``. Used as a contact/proximity tolerance for the SAT test.

        Raises:
            ValueError: if ``margin`` is negative.
        """
        if margin < 0.0:
            raise ValueError("expanded: margin must be non-negative")

        h = self._half_extents
        return OrientedBoundingBox.from_frame_and_half_extents(
            self._frame,
            Vector3D(h.x + margin, h.y + margin, h.z + margin),
        )

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, OrientedBoundingBox):
            return NotImplemented
        return (
            self._frame.origin == other._frame.origin
            and self._frame.axis_x == other._frame.axis_x
            and self._frame.axis_y == other._frame.axis_y
            and self._frame.axis_z == other._frame.axis_z
            and self._half_extents == other._half_extents
        )

    def __ne__(self, other: object) -> bool:
        result = self.__eq__(other)
        if result is NotImplemented:
            return result
        return not result

    # ------------------------------------------------------------------
    # String representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"OrientedBoundingBox(center={self._frame.origin}, "
            f"axis_x={self._frame.axis_x}, "
            f"axis_y={self._frame.axis_y}, "
            f"axis_z={self._frame.axis_z}, "
            f"half_extents={self._half_extents})"
        )

    def __str__(self) -> str:
        return self.__repr__()


def _obb_obb_sat(a: OrientedBoundingBox, b: OrientedBoundingBox) -> bool:
    """OBB-OBB separating axis test (Gottschalk 1996; Ericson RTCD 4.4.1).

    Tests all 15 potential separating axes: 3 from each box plus 9 pairwise
    cross products. A small epsilon is added to the absolute rotation matrix
    to make near-parallel edge tests numerically robust.
    """
    a_axes = (a.frame.axis_x, a.frame.axis_y, a.frame.axis_z)
    b_axes = (b.frame.axis_x, b.frame.axis_y, b.frame.axis_z)
    a_he = (a.half_extents.x, a.half_extents.y, a.half_extents.z)
    b_he = (b.half_extents.x, b.half_extents.y, b.half_extents.z)

    R = [[a_axes[i].dot(b_axes[j]) for j in range(3)] for i in range(3)]
    abs_R = [[abs(R[i][j]) + _SAT_PARALLEL_EPSILON for j in range(3)] for i in range(3)]

    t_world = b.frame.origin - a.frame.origin
    t = (
        t_world.dot(a_axes[0]),
        t_world.dot(a_axes[1]),
        t_world.dot(a_axes[2]),
    )

    for i in range(3):
        ra = a_he[i]
        rb = b_he[0] * abs_R[i][0] + b_he[1] * abs_R[i][1] + b_he[2] * abs_R[i][2]
        if abs(t[i]) > ra + rb:
            return False

    for j in range(3):
        ra = a_he[0] * abs_R[0][j] + a_he[1] * abs_R[1][j] + a_he[2] * abs_R[2][j]
        rb = b_he[j]
        tj = t[0] * R[0][j] + t[1] * R[1][j] + t[2] * R[2][j]
        if abs(tj) > ra + rb:
            return False

    for i in range(3):
        i1 = (i + 1) % 3
        i2 = (i + 2) % 3
        for j in range(3):
            j1 = (j + 1) % 3
            j2 = (j + 2) % 3
            ra = a_he[i1] * abs_R[i2][j] + a_he[i2] * abs_R[i1][j]
            rb = b_he[j1] * abs_R[i][j2] + b_he[j2] * abs_R[i][j1]
            t_proj = abs(t[i2] * R[i1][j] - t[i1] * R[i2][j])
            if t_proj > ra + rb:
                return False

    return True

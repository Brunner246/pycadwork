# Geometry

A self-contained geometry layer of value-types — usable on its own, with no
cadwork process involved:

- **`Point3D`** — a position. Supports `Point + Vector → Point`,
  `Point − Point → Vector`, epsilon-based equality, and `distance_to`.
- **`Vector3D`** — magnitude/direction with the usual vector algebra.
- **`Frame3D`** — an origin plus orthonormal axes (a local coordinate frame).
- **`Plane3D`**, **`Line3D`**, **`Segment3D`**, **`Loop`**, **`Face`** — the
  classic primitives.
- **`Brep`** — a boundary representation built from cadwork facet lists.
- **`AxisAlignedBoundingBox`** / **`OrientedBoundingBox`** — with
  `expanded(tolerance)` for tolerance-grown queries.
- **`RTreeIndex3D`** (a `SpatialIndex3D`) — an R-tree over element AABBs for fast
  spatial pruning, backed by [`rtree`](https://pypi.org/project/Rtree/).
- **Creation specs** — `RectSection`, `PanelSection`, `AxisPoints`, `AxisFrame`,
  `Segment` — frozen parameter objects bundling the arguments that flow into
  `create_*` calls, consumed identically by the domain classmethods, the
  adapter, and the fake.

```python
from pycadwork import Point3D, Vector3D

a = Point3D(0, 0, 0)
b = Point3D(3, 4, 0)
displacement = b - a  # Vector3D(3, 4, 0)
moved = a + Vector3D(0, 0, 1)  # Point3D(0, 0, 1)
a.distance_to(b)  # 5.0
```

"""Parameter-object specs for element creation.

These bundle the geometric arguments that flow into backend create_* calls.
Same instance shape is consumed by domain classmethods, the protocol, the
cwapi3d adapter, and the fake — eliminating the per-call _t()/_v() unpacking.
"""
from __future__ import annotations

from dataclasses import dataclass

from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.vector3d import Vector3D


@dataclass(frozen=True, slots=True)
class AxisPoints:
    """Three points defining a beam/panel local frame (origin, +x, +xz-plane)."""

    p1: Point3D
    p2: Point3D
    p3: Point3D


@dataclass(frozen=True, slots=True)
class AxisFrame:
    """Origin + x/z directions + length — the vector form of an axis frame."""

    origin: Point3D
    x_dir: Vector3D
    z_dir: Vector3D
    length: float


@dataclass(frozen=True, slots=True)
class Segment:
    """A two-point line segment — used for drillings and lines."""

    p1: Point3D
    p2: Point3D


@dataclass(frozen=True, slots=True)
class RectSection:
    """Rectangular beam cross-section."""

    width: float
    height: float


@dataclass(frozen=True, slots=True)
class PanelSection:
    """Panel cross-section (cadwork uses `thickness`, not `height`)."""

    width: float
    thickness: float

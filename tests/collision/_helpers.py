"""Shared beam factory for the collision tests.

Beams run axis-aligned along +X from ``p1`` so the fake's vertex generation
yields a predictable box ``[x, x+length] x [y, y+width] x [z, z+height]`` —
letting us position elements to touch, gap, or overlap deterministically. Same
convention as ``tests/connectivity/test_find.py``.
"""

from __future__ import annotations

from pycadwork import AxisPoints, Beam, Point3D, RectSection


def beam(
    x: float,
    y: float,
    z: float,
    length: float,
    width: float = 10.0,
    height: float = 10.0,
) -> Beam:
    return Beam.create_rectangular(
        RectSection(width, height),
        AxisPoints(
            Point3D(x, y, z),
            Point3D(x + length, y, z),
            Point3D(x, y, z + 1.0),
        ),
    )

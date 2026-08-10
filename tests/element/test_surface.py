"""Surface create + factory round-trip."""

from __future__ import annotations

from pycadwork import Point3D, Surface, from_id


def test_create_returns_surface():
    surf = Surface.create(
        [
            Point3D(0, 0, 0),
            Point3D(1000, 0, 0),
            Point3D(1000, 1000, 0),
            Point3D(0, 1000, 0),
        ]
    )
    assert isinstance(surf, Surface)
    assert surf.id >= 1


def test_from_id_rewraps_as_surface():
    surf = Surface.create([Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 1000, 0)])
    assert isinstance(from_id(surf.id), Surface)

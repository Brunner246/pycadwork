"""AuxiliaryElement create + factory round-trip."""

from __future__ import annotations

from pycadwork import AuxiliaryElement, Point3D, Surface, Vector3D, from_id


def _square() -> Surface:
    return Surface.create(
        [
            Point3D(0, 0, 0),
            Point3D(1000, 0, 0),
            Point3D(1000, 1000, 0),
            Point3D(0, 1000, 0),
        ]
    )


def test_from_surface_extrusion_returns_auxiliary():
    aux = AuxiliaryElement.from_surface_extrusion(_square(), Vector3D(0, 0, 100))
    assert isinstance(aux, AuxiliaryElement)


def test_from_id_rewraps_as_auxiliary():
    aux = AuxiliaryElement.from_surface_extrusion(_square(), Vector3D(0, 0, 250))
    assert isinstance(from_id(aux.id), AuxiliaryElement)

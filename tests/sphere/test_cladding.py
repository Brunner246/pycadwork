"""Gapped triangular cladding panels."""

from __future__ import annotations

import pytest

from pycadwork import Point3D
from pycadwork.element.plate import Plate
from pycadwork.gridshell import GridTopology
from pycadwork.sphere import faces_to_surfaces, icosphere_faces
from pycadwork.sphere.cladding import _inset_triangle, build_cladding
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _topology(faces):
    surfaces = faces_to_surfaces(faces)
    return GridTopology.from_breps([s.geometry.brep for s in surfaces])


def _inradius(a: Point3D, b: Point3D, c: Point3D) -> float:
    side_a = float(b.distance_to(c))
    side_b = float(c.distance_to(a))
    side_c = float(a.distance_to(b))
    semi = (side_a + side_b + side_c) / 2.0
    area = 0.5 * float((b - a).cross(c - a).magnitude())
    return area / semi


# ---- the inset math (uniform gap on every side) ----


def test_inset_reduces_the_inradius_by_exactly_the_inset():
    tri = [Point3D(0, 0, 0), Point3D(300, 0, 0), Point3D(0, 300, 0)]
    before = _inradius(*tri)
    inset = 10.0
    shrunk = _inset_triangle(tri, inset)
    assert shrunk is not None
    assert _inradius(*shrunk) == pytest.approx(before - inset)


def test_inset_too_large_for_the_triangle_returns_none():
    tri = [Point3D(0, 0, 0), Point3D(300, 0, 0), Point3D(0, 300, 0)]
    assert _inset_triangle(tri, _inradius(*tri) + 1.0) is None


# ---- build_cladding ----


def test_one_panel_per_face():
    topology = _topology(icosphere_faces(1000.0, 1))  # 20 faces
    panels, warnings = build_cladding(
        topology, thickness=20.0, gap=15.0, center=Point3D.origin()
    )
    assert len(panels) == 20
    assert all(isinstance(p, Plate) for p in panels)
    assert not warnings


def test_panels_carry_the_requested_thickness(fake_cadwork: FakeCadworkAdapter):
    topology = _topology(icosphere_faces(1000.0, 1))
    panels, _ = build_cladding(
        topology, thickness=27.0, gap=10.0, center=Point3D.origin()
    )
    for panel in panels:
        assert fake_cadwork.state.elements[panel.id].height == pytest.approx(27.0)


def test_gap_too_large_skips_every_panel_with_a_warning():
    topology = _topology(icosphere_faces(1000.0, 1))
    panels, warnings = build_cladding(
        topology, thickness=20.0, gap=1_000_000.0, center=Point3D.origin()
    )
    assert panels == []
    assert len(warnings) == 20
    assert all("too small for the gap" in w for w in warnings)


def test_cladding_rejects_bad_arguments():
    topology = _topology(icosphere_faces(1000.0, 1))
    with pytest.raises(ValueError, match="thickness must be positive"):
        build_cladding(topology, thickness=0.0, gap=10.0, center=Point3D.origin())
    with pytest.raises(ValueError, match="gap must not be negative"):
        build_cladding(topology, thickness=20.0, gap=-1.0, center=Point3D.origin())

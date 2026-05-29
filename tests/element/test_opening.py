"""Opening create + factory round-trip (dispatch precedence over Plate)."""
from __future__ import annotations

from pycadwork import AxisPoints, Opening, PanelSection, Plate, Point3D, from_id


def test_create_rectangular_returns_opening():
    opening = Opening.create_rectangular(
        PanelSection(800.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(800, 0, 0), Point3D(0, 0, 1)),
    )
    assert isinstance(opening, Opening)


def test_snapshot_has_both_panel_and_opening_flags():
    opening = Opening.create_rectangular(
        PanelSection(800.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(800, 0, 0), Point3D(0, 0, 1)),
    )
    snap = opening.cadwork_type
    assert snap.is_panel
    assert snap.is_opening


def test_from_id_returns_opening_not_plate():
    opening = Opening.create_rectangular(
        PanelSection(800.0, 18.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(800, 0, 0), Point3D(0, 0, 1)),
    )
    wrapped = from_id(opening.id)
    assert isinstance(wrapped, Opening)
    assert not isinstance(wrapped, Plate) or type(wrapped) is Opening

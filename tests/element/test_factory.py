"""Factory dispatch: from_id wraps each ID in the most specific subclass."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from pycadwork import (
    AuxiliaryElement,
    AxisPoints,
    Beam,
    ConnectorAxis,
    Drilling,
    Element,
    Opening,
    PanelSection,
    Plate,
    Point3D,
    RectSection,
    Segment,
    Surface,
    Vector3D,
    Wall,
    from_id,
)
from pycadwork.cadwork_adapter import cadwork
from pycadwork.cadwork_adapter.types import CoverKind, ElementTypeSnapshot


def test_from_id_returns_beam_for_beam():
    beam = Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    wrapped = from_id(beam.id)
    assert isinstance(wrapped, Beam)
    assert wrapped.id == beam.id


def test_from_id_returns_plate_for_panel():
    plate = Plate.create_rectangular(
        PanelSection(600, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
    )
    assert isinstance(from_id(plate.id), Plate)


def test_from_id_returns_drilling_for_drilling():
    d = Drilling.create(10, Segment(Point3D(0, 0, 0), Point3D(0, 0, 100)))
    assert isinstance(from_id(d.id), Drilling)


def test_from_id_returns_wall_for_framed_wall_flagged_element():
    beam = Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    cadwork.attributes.set_cover_kind([beam.id], CoverKind.FRAMED_WALL)
    wrapped = from_id(beam.id)
    assert isinstance(wrapped, Wall)


def test_from_id_returns_opening_for_panel_marked_as_opening():
    plate = Plate.create_rectangular(
        PanelSection(800, 18),
        AxisPoints(Point3D(0, 0, 0), Point3D(800, 0, 0), Point3D(0, 0, 1)),
    )
    cadwork.attributes.set_opening([plate.id])
    wrapped = from_id(plate.id)
    assert isinstance(wrapped, Opening)
    assert type(wrapped) is Opening


def test_from_id_returns_connector_axis_over_beam():
    cxn = ConnectorAxis.create_standard(
        Segment(Point3D(0, 0, 0), Point3D(0, 0, 200)), "M16"
    )
    wrapped = from_id(cxn.id)
    assert isinstance(wrapped, ConnectorAxis)
    assert type(wrapped) is ConnectorAxis


def test_from_id_returns_auxiliary_for_auxiliary_element():
    surf = Surface.create(
        [Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 1000, 0)]
    )
    aux = AuxiliaryElement.from_surface_extrusion(surf, Vector3D(0, 0, 100))
    wrapped = from_id(aux.id)
    assert isinstance(wrapped, AuxiliaryElement)


def test_from_id_returns_surface_for_surface():
    surf = Surface.create(
        [Point3D(0, 0, 0), Point3D(1000, 0, 0), Point3D(0, 1000, 0)]
    )
    assert isinstance(from_id(surf.id), Surface)


def test_unknown_type_falls_back_to_bare_element_with_warning(fake_cadwork):
    # An element whose snapshot matches no registered predicate.
    el = fake_cadwork.elements._state.alloc(ElementTypeSnapshot())
    with pytest.warns(UserWarning, match="no specific subclass matched"):
        wrapped = from_id(el.eid)
    assert type(wrapped) is Element


def test_from_id_shares_the_snapshot_it_paid_for(fake_cadwork):
    beam = Beam.create_rectangular(
        RectSection(80, 200),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )
    with patch.object(
        fake_cadwork.elements,
        "get_element_type",
        wraps=fake_cadwork.elements.get_element_type,
    ) as spy:
        wrapped = from_id(beam.id)
        # The cached snapshot is reused — touching cadwork_type does not re-query.
        _ = wrapped.cadwork_type

    spy.assert_called_once_with(beam.id)

"""ConnectorAxis create + factory round-trip (dispatch precedence over Beam)."""

from __future__ import annotations

from pycadwork import Beam, ConnectorAxis, Point3D, Segment, from_id


def test_create_standard_returns_connector_axis():
    cxn = ConnectorAxis.create_standard(
        Segment(Point3D(0, 0, 0), Point3D(0, 0, 200)), "M16"
    )
    assert isinstance(cxn, ConnectorAxis)


def test_from_id_returns_connector_axis_not_beam():
    cxn = ConnectorAxis.create_standard(
        Segment(Point3D(0, 0, 0), Point3D(0, 0, 200)), "M12"
    )
    wrapped = from_id(cxn.id)
    assert isinstance(wrapped, ConnectorAxis)
    assert type(wrapped) is ConnectorAxis
    assert not isinstance(wrapped, Beam)

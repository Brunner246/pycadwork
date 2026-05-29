"""Round-trip the attribute surface (cadwork_guid, additional_data,
assembly_number, user_attribute) against the fake backend, via ``beam.attrs``.
"""
from __future__ import annotations

from pycadwork import AxisPoints, Beam, Point3D, RectSection


def _make_beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


def test_cadwork_guid_is_assigned_at_creation_and_read_only():
    beam = _make_beam()
    guid = beam.attrs.cadwork_guid
    assert guid  # non-empty
    # Fake backend issues a stable per-element GUID; reading again returns the same.
    assert beam.attrs.cadwork_guid == guid


def test_two_elements_get_distinct_cadwork_guids():
    a, b = _make_beam(), _make_beam()
    assert a.attrs.cadwork_guid != b.attrs.cadwork_guid


def test_additional_data_round_trip():
    beam = _make_beam()
    assert beam.attrs.additional_data == ""
    beam.attrs.set_additional_data("payload-7")
    assert beam.attrs.additional_data == "payload-7"


def test_assembly_number_round_trip():
    beam = _make_beam()
    beam.attrs.set_assembly_number("A-42")
    assert beam.attrs.assembly_number == "A-42"


def test_user_attribute_round_trip_per_index():
    beam = _make_beam()
    beam.attrs.set_user_attribute(1, "alpha")
    beam.attrs.set_user_attribute(2, "beta")
    assert beam.attrs.user_attribute(1) == "alpha"
    assert beam.attrs.user_attribute(2) == "beta"
    # Unset indices return "" (the fake's default).
    assert beam.attrs.user_attribute(99) == ""

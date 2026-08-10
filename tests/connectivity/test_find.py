"""Tests for pycadwork.find_connected.

Beams are placed axis-aligned (running along +X from ``p1``) so the fake's
vertex generation yields a predictable box ``[x, x+length] x [y, y+width] x
[z, z+height]`` — letting us position elements to touch, gap, or overlap
deterministically.
"""

from __future__ import annotations

from pycadwork import AxisPoints, Beam, Point3D, RectSection, find_connected


def _beam(
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


def test_touching_beams_are_connected():
    a = _beam(0, 0, 0, 100)
    b = _beam(100, 0, 0, 100)  # flush against a's far end
    assert find_connected(a, among=[a, b]) == [b]


def test_overlapping_beams_are_connected():
    a = _beam(0, 0, 0, 100)
    b = _beam(50, 0, 0, 100)  # overlaps a on [50, 100]
    assert find_connected(a, among=[a, b]) == [b]


def test_gapped_beams_are_not_connected_by_default():
    a = _beam(0, 0, 0, 100)
    c = _beam(105, 0, 0, 100)  # 5-unit gap
    assert find_connected(a, among=[a, c]) == []


def test_tolerance_bridges_a_gap():
    a = _beam(0, 0, 0, 100)
    c = _beam(105, 0, 0, 100)  # 5-unit gap
    assert find_connected(a, among=[a, c], tolerance=10.0) == [c]


def test_element_itself_is_never_returned():
    a = _beam(0, 0, 0, 100)
    assert find_connected(a, among=[a]) == []


def test_among_restricts_the_search_scope():
    a = _beam(0, 0, 0, 100)
    b = _beam(100, 0, 0, 100)  # touches a along X
    _on_top = _beam(0, 0, 10, 100)  # also touches a, but excluded from `among`
    assert find_connected(a, among=[a, b]) == [b]


def test_default_searches_the_active_model():
    a = _beam(0, 0, 0, 100)
    b = _beam(100, 0, 0, 100)  # touches a
    _far = _beam(1000, 1000, 1000, 100)  # nowhere near a
    assert set(find_connected(a)) == {b}


def test_custom_predicate_overrides_geometry():
    a = _beam(0, 0, 0, 100)
    b = _beam(1000, 0, 0, 100)  # geometrically disjoint
    c = _beam(2000, 0, 0, 100)  # geometrically disjoint
    found = find_connected(a, among=[a, b, c], connects=lambda _x, _y: True)
    assert set(found) == {b, c}


def test_custom_predicate_still_excludes_self():
    a = _beam(0, 0, 0, 100)
    assert find_connected(a, among=[a], connects=lambda _x, _y: True) == []

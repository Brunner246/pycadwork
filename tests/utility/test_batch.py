"""batch_apply against FakeCadworkAdapter — one adapter call per attribute."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from pycadwork import AxisPoints, Beam, Point3D, RectSection, batch_apply


def _make_beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


def test_single_attribute_makes_one_call(fake_cadwork):
    beams = [_make_beam(), _make_beam(), _make_beam()]
    with patch.object(fake_cadwork.attributes, "set_group", wraps=fake_cadwork.attributes.set_group) as spy:
        batch_apply(beams, group="frame")

    spy.assert_called_once_with([b.id for b in beams], "frame")
    for b in beams:
        assert b.attrs.group == "frame"


def test_multiple_attributes_one_call_each(fake_cadwork):
    beams = [_make_beam(), _make_beam()]
    ids = [b.id for b in beams]
    attrs = fake_cadwork.attributes
    with patch.object(attrs, "set_group", wraps=attrs.set_group) as group_spy, \
         patch.object(attrs, "set_material_name", wraps=attrs.set_material_name) as material_spy, \
         patch.object(attrs, "set_production_number", wraps=attrs.set_production_number) as prod_spy:
        batch_apply(beams, group="frame", material_name="Pine", production_number=42)

    group_spy.assert_called_once_with(ids, "frame")
    material_spy.assert_called_once_with(ids, "Pine")
    prod_spy.assert_called_once_with(ids, 42)


def test_empty_iterable_makes_no_adapter_calls(fake_cadwork):
    attrs = fake_cadwork.attributes
    with patch.object(attrs, "set_group", wraps=attrs.set_group) as group_spy, \
         patch.object(attrs, "set_material_name", wraps=attrs.set_material_name) as material_spy:
        batch_apply([], group="frame", material_name="Pine")

    group_spy.assert_not_called()
    material_spy.assert_not_called()


def test_unknown_attribute_raises_typeerror(fake_cadwork):
    beam = _make_beam()
    with pytest.raises(TypeError, match="weight"):
        batch_apply([beam], weight=12.0)


def test_works_with_generator_input(fake_cadwork):
    beams = [_make_beam() for _ in range(3)]
    attrs = fake_cadwork.attributes
    with patch.object(attrs, "set_name", wraps=attrs.set_name) as spy:
        batch_apply((b for b in beams), name="Stud")

    spy.assert_called_once_with([b.id for b in beams], "Stud")


def test_supports_all_documented_attributes(fake_cadwork):
    beam = _make_beam()
    ids = [beam.id]
    attrs = fake_cadwork.attributes
    names = [
        "set_name", "set_group", "set_subgroup", "set_comment",
        "set_material_name", "set_sku", "set_production_number", "set_part_number",
    ]
    spies = {name: patch.object(attrs, name, wraps=getattr(attrs, name)) for name in names}
    entered = {name: spy.__enter__() for name, spy in spies.items()}
    try:
        batch_apply(
            [beam],
            name="N",
            group="G",
            subgroup="S",
            comment="C",
            material_name="M",
            sku="K",
            production_number=7,
            part_number="P",
        )
    finally:
        for spy in spies.values():
            spy.__exit__(None, None, None)

    entered["set_name"].assert_called_once_with(ids, "N")
    entered["set_group"].assert_called_once_with(ids, "G")
    entered["set_subgroup"].assert_called_once_with(ids, "S")
    entered["set_comment"].assert_called_once_with(ids, "C")
    entered["set_material_name"].assert_called_once_with(ids, "M")
    entered["set_sku"].assert_called_once_with(ids, "K")
    entered["set_production_number"].assert_called_once_with(ids, 7)
    entered["set_part_number"].assert_called_once_with(ids, "P")

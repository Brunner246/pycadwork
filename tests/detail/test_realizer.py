"""build_detail orders its steps so the calculation never sees a broken cover.

Driven entirely through the FakeModuleAdapter / FakeState — no running cadwork.
The post-conditions pin the two real hazards: members are grouped under a
cover that is flagged with the right kind, and the calculation only runs once
that holds (and only when there is something to calculate).
"""

from __future__ import annotations

import json
from pathlib import Path

from pycadwork.cadwork_adapter.types import CoverKind, DetailType
from pycadwork.detail import DetailBuilder, build_detail, load_definition, save_detail
from pycadwork.detail.properties import Distribution, ModuleProperties
from pycadwork.element.factory import from_id
from pycadwork.geometry import AxisPoints, PanelSection, Point3D, RectSection
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _wall_detail() -> DetailBuilder:
    return (
        DetailBuilder()
        .named("corner")
        .of_type(DetailType.CORNER_DETAIL)
        .cover(CoverKind.FRAMED_WALL)
        .add_beam(
            RectSection(60, 120),
            AxisPoints(Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)),
            role="stud",
        )
        .add_panel(
            PanelSection(600, 15),
            AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
            role="sheathing",
        )
    )


def test_build_creates_members_cover_and_runs_calculation(
    fake_cadwork: FakeCadworkAdapter,
):
    result = build_detail(_wall_detail().build())

    assert len(result.member_ids) == 2
    assert result.cover_id is not None
    assert result.calculated

    # The cover is flagged with the definition's kind.
    cover = from_id(result.cover_id)
    assert cover.cadwork_type.is_framed_wall

    # Every member shares the cover's grouping key (the cover-membership link).
    cover_group = fake_cadwork.state.elements[result.cover_id].group
    assert cover_group
    for mid in result.member_ids:
        assert fake_cadwork.state.elements[mid].group == cover_group

    # The calculation ran (silently, by default) on exactly the cover.
    assert fake_cadwork.state.module_silent_calculation_calls == [[result.cover_id]]
    assert fake_cadwork.state.module_calculation_calls == []


def test_properties_applied_for_every_member_before_calculation(
    fake_cadwork: FakeCadworkAdapter,
):
    result = build_detail(_wall_detail().build())

    applied_ids = {eid for ids, _ in fake_cadwork.state.module_applied for eid in ids}
    assert applied_ids == set(result.member_ids)
    # Calculation only after properties exist.
    assert fake_cadwork.state.module_silent_calculation_calls


def test_properties_batched_one_call_per_distinct_value(
    fake_cadwork: FakeCadworkAdapter,
):
    shared = ModuleProperties(distribute_in_axis=Distribution(active=True, distance=625))
    definition = (
        DetailBuilder()
        .named("two-studs")
        .of_type(DetailType.CORNER_DETAIL)
        .cover(CoverKind.FRAMED_WALL)
        .add_beam(
            RectSection(60, 120),
            AxisPoints(Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)),
            properties=shared,
        )
        .add_beam(
            RectSection(60, 120),
            AxisPoints(Point3D(625, 0, 0), Point3D(625, 0, 2500), Point3D(1, 0, 0)),
            properties=shared,
        )
        .build()
    )
    build_detail(definition)
    # Both members carry the identical value -> a single batched apply call.
    assert len(fake_cadwork.state.module_applied) == 1
    ids, props = fake_cadwork.state.module_applied[0]
    assert len(ids) == 2
    assert props == shared


def test_detail_path_set_when_supplied(fake_cadwork: FakeCadworkAdapter):
    build_detail(_wall_detail().build(), detail_path="C:/details")
    assert fake_cadwork.state.module_detail_path == "C:/details"


def test_detail_path_left_untouched_when_omitted(fake_cadwork: FakeCadworkAdapter):
    build_detail(_wall_detail().build())
    assert fake_cadwork.state.module_detail_path is None


def test_calculate_false_skips_calculation(fake_cadwork: FakeCadworkAdapter):
    result = build_detail(_wall_detail().build(), calculate=False)
    assert not result.calculated
    assert fake_cadwork.state.module_silent_calculation_calls == []
    assert fake_cadwork.state.module_calculation_calls == []


def test_non_silent_calculation_uses_loud_channel(fake_cadwork: FakeCadworkAdapter):
    result = build_detail(_wall_detail().build(), silent=False)
    assert fake_cadwork.state.module_calculation_calls == [[result.cover_id]]
    assert fake_cadwork.state.module_silent_calculation_calls == []


def test_save_detail_writes_loadable_json(tmp_path: Path):
    definition = _wall_detail().build()
    path = tmp_path / "detail.json"
    save_detail(definition, str(path))
    assert load_definition(json.loads(path.read_text(encoding="utf-8"))) == definition


def test_empty_definition_creates_no_cover_and_no_calculation(
    fake_cadwork: FakeCadworkAdapter,
):
    definition = (
        DetailBuilder()
        .named("empty")
        .of_type(DetailType.CORNER_DETAIL)
        .cover(CoverKind.FRAMED_WALL)
        .build()
    )
    result = build_detail(definition)
    assert result.member_ids == ()
    assert result.cover_id is None
    assert not result.calculated
    assert fake_cadwork.state.module_silent_calculation_calls == []

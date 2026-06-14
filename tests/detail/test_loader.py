"""The loader seam selects loaders by (schema, version) with a ``*`` fallback."""

from __future__ import annotations

import pytest

from pycadwork.cadwork_adapter.types import CoverKind, DetailType
from pycadwork.detail import load_definition
from pycadwork.detail.definition import DetailDefinition, MemberSpec
from pycadwork.detail.loader import (
    LoaderRegistry,
    UnknownSchemaError,
    register_loader,
)
from pycadwork.geometry import AxisPoints, Point3D, RectSection


def test_native_loader_selected_for_native_schema():
    definition = DetailDefinition(
        name="corner",
        detail_type=DetailType.CORNER_DETAIL,
        cover_kind=CoverKind.FRAMED_WALL,
        members=(
            MemberSpec(
                kind="beam",
                section=RectSection(60, 120),
                points=AxisPoints(
                    Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)
                ),
                role="stud",
            ),
        ),
    )
    assert load_definition(definition.to_dict()) == definition


def test_version_star_fallback_resolves():
    # The native loader registers "*", so an unseen version still resolves.
    raw = DetailDefinition(
        name="x",
        detail_type=DetailType.NO_DETAIL,
        cover_kind=CoverKind.FRAMED_WALL,
    ).to_dict()
    raw["schema_version"] = "99.unknown"
    assert load_definition(raw).name == "x"


def test_unknown_schema_raises():
    with pytest.raises(UnknownSchemaError, match="no loader"):
        load_definition({"schema": "vendor.unheard-of", "schema_version": "1"})


def test_missing_schema_key_raises():
    with pytest.raises(UnknownSchemaError, match="no 'schema'"):
        load_definition({"name": "x"})


def test_foreign_schema_maps_to_internal_definition():
    raw = {
        "schema": "example.timberframe",
        "schema_version": "2",
        "id": "ext-corner",
        "situation": "corner",
        "wall_type": "framed",
        "parts": [
            {
                "shape": "stick",
                "function": "stud",
                "size": {"b": 60, "h": 120},
                "line": {"from": [0, 0, 0], "to": [0, 0, 2500], "up": [1, 0, 0]},
            },
            {
                "shape": "board",
                "function": "sheathing",
                "size": {"b": 600, "t": 15},
                "line": {"from": [0, 0, 0], "to": [2400, 0, 0], "up": [0, 0, 1]},
            },
        ],
    }
    definition = load_definition(raw)
    assert definition.name == "ext-corner"
    assert definition.detail_type is DetailType.CORNER_DETAIL
    assert definition.cover_kind is CoverKind.FRAMED_WALL
    assert [m.kind for m in definition.members] == ["beam", "panel"]
    assert [m.role for m in definition.members] == ["stud", "sheathing"]


def test_registry_prefers_exact_version_over_star():
    registry = LoaderRegistry()

    class _Base:
        schema = "vendor.x"

        def __init__(self, tag):
            self._tag = tag

        def load(self, raw):
            return self._tag

    exact = _Base("exact")
    exact.versions = ("1",)
    star = _Base("star")
    star.versions = ("*",)
    registry.register(star)
    registry.register(exact)

    assert registry.resolve("vendor.x", "1") is exact
    assert registry.resolve("vendor.x", "2") is star


def test_register_loader_decorator_registers_in_global_registry():
    @register_loader
    class _Probe:
        schema = "test.probe"
        versions = ("1",)

        def load(self, raw):
            return DetailDefinition(
                name=raw["name"],
                detail_type=DetailType.NO_DETAIL,
                cover_kind=CoverKind.FRAMED_WALL,
            )

    out = load_definition({"schema": "test.probe", "schema_version": "1", "name": "p"})
    assert out.name == "p"

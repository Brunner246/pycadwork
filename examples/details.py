"""Element-module details — author, serialize, share, and realize.

A *detail* is a parametric timber-frame situation (a corner, a T-junction, an
opening, …) that cadwork's element module expands into real framing inside a
wall/floor/roof. ``pycadwork.detail`` lets you describe one as a pure, shareable
:class:`DetailDefinition`, round-trip it through JSON (native *or* a foreign
vendor schema), and realize it end-to-end against the model.

    uv run python -m examples.details

.. note::

   Realizing a detail standalone fabricates a placeholder *host cover* and runs
   ``start_element_module_calculation`` through the version-isolation seam — the
   bits a real project gets from an existing wall and the cadwork UI. Those seam
   touches are marked below; they are not part of normal day-to-day use.
"""

from __future__ import annotations

import json

from pycadwork import (
    AxisPoints,
    CoverKind,
    PanelSection,
    Point3D,
    RectSection,
)
from pycadwork.detail import (
    DetailBuilder,
    DetailDefinition,
    DetailType,
    build_detail,
    load_definition,
)


def _framed_wall_corner() -> DetailDefinition:
    """Author a framed-wall corner detail with the fluent builder.

    Members carry *roles* (``stud``, ``sheathing``, …) — named presets that
    resolve to element-module properties, so you describe intent, not flags.
    """
    return (
        DetailBuilder()
        .named("framed-wall-corner")
        .of_type(DetailType.CORNER_DETAIL)
        .cover(CoverKind.FRAMED_WALL)
        .metadata(author="examples", units="mm")
        .add_beam(
            RectSection(60, 120),
            AxisPoints(Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)),
            role="bottom_plate",
            name="sole plate",
        )
        .add_beam(
            RectSection(60, 120),
            AxisPoints(Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(1, 0, 0)),
            role="stud",
            name="corner stud",
        )
        .add_panel(
            PanelSection(600, 15),
            AxisPoints(Point3D(0, 0, 0), Point3D(2400, 0, 0), Point3D(0, 0, 1)),
            role="sheathing",
            name="OSB",
        )
        .build()
    )


def demo_author_with_builder() -> None:
    """The builder validates detail_type<->cover_kind coherence as it builds."""
    detail = _framed_wall_corner()
    print("authored", detail.name, "with", len(detail.members), "members")
    print("roles    =", [m.role for m in detail.members])


def demo_serialize_roundtrip() -> None:
    """A definition is pure data: ``to_json`` / ``from_json`` round-trips exactly."""
    detail = _framed_wall_corner()
    text = detail.to_json()
    print("serialized", len(text), "chars of JSON")
    assert DetailDefinition.from_json(text) == detail
    print("round-trip identical:", True)


def demo_load_native_json() -> None:
    """``load_definition`` dispatches by the payload's ``schema`` field."""
    raw = json.loads(_framed_wall_corner().to_json())
    detail = load_definition(raw)  # schema == "pycadwork.detail"
    print("loaded native schema:", detail.schema, "->", detail.name)


def demo_realize_framed_wall_detail() -> None:
    """Realize the detail: create members, group on a host cover, calculate.

    ``build_detail`` runs the whole pipeline through the seam — the calculation
    call mimics what the cadwork element module does in a real wall.
    """
    detail = _framed_wall_corner()
    result = build_detail(detail, detail_path=None, calculate=True, silent=True)
    print("realized members =", result.member_ids)
    print("host cover id    =", result.cover_id)
    print("calculation ran  =", result.calculated)


def demo_load_foreign_schema() -> None:
    """A foreign vendor schema maps to the same internal definition via a loader.

    The ``example.timberframe`` loader is the documented extension point — a
    third party teaches pycadwork their JSON by writing one ``DefinitionLoader``.
    """
    foreign = {
        "schema": "example.timberframe",
        "schema_version": "2",
        "id": "vendor-corner",
        "situation": "corner",
        "wall_type": "framed",
        "parts": [
            {
                "shape": "stick",
                "function": "stud",
                "size": {"b": 60, "h": 120},
                "line": {"from": [0, 0, 0], "to": [0, 0, 2500], "up": [1, 0, 0]},
            },
        ],
    }
    detail = load_definition(foreign)
    print("foreign ->", detail.name, detail.detail_type.name, detail.cover_kind.name)
    print("mapped role =", detail.members[0].role)


def run() -> None:
    """Run every detail demo in order."""
    demo_author_with_builder()
    demo_serialize_roundtrip()
    demo_load_native_json()
    demo_realize_framed_wall_detail()
    demo_load_foreign_schema()


if __name__ == "__main__":
    run()

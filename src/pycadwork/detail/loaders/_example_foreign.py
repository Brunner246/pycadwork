"""A worked example of a *foreign-schema* loader — the third-party contract.

This is the skeleton a vendor copies to teach pycadwork their own timber-frame
JSON. It is intentionally concrete (and registered) so the test-suite and
``examples/details.py`` can exercise the seam end to end, but every mapping here
is illustrative: a real loader substitutes its own field names.

The three translation jobs a loader does:

1. **situation / cover** — map the foreign situation + wall family onto the
   internal :class:`DetailType` and :class:`CoverKind`;
2. **roles** — map foreign *function* strings onto pycadwork
   :mod:`~pycadwork.detail.roles` names, which resolve to
   :class:`ModuleProperties` presets (so the foreign source need not know any
   property flags);
3. **geometry** — map foreign section/axis fields onto :class:`RectSection` /
   :class:`PanelSection` and :class:`AxisPoints`.
"""

from __future__ import annotations

from typing import Any

from pycadwork.cadwork_adapter.types import CoverKind, DetailType
from pycadwork.detail.builder import DetailBuilder
from pycadwork.detail.definition import DetailDefinition
from pycadwork.detail.loader import register_loader
from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.specs import AxisPoints, PanelSection, RectSection

# Foreign "situation" -> internal DetailType.
_SITUATIONS: dict[str, DetailType] = {
    "corner": DetailType.CORNER_DETAIL,
    "tee": DetailType.T_DETAIL,
    "cross": DetailType.CROSS_DETAIL,
    "edge": DetailType.EDGE_DETAIL,
    "end": DetailType.END_DETAIL,
    "opening": DetailType.OPENING_DETAIL,
}

# Foreign "wall_type" -> internal CoverKind.
_WALL_TYPES: dict[str, CoverKind] = {
    "framed": CoverKind.FRAMED_WALL,
    "solid": CoverKind.SOLID_WALL,
    "log": CoverKind.LOG_WALL,
}

# Foreign "function" -> pycadwork role name.
_FUNCTIONS: dict[str, str] = {
    "sole_plate": "bottom_plate",
    "head_plate": "top_plate",
    "stud": "stud",
    "sheathing": "sheathing",
    "cutter": "cutting_element",
}


def _axis(line: dict[str, Any]) -> AxisPoints:
    a, b, up = line["from"], line["to"], line["up"]
    return AxisPoints(
        Point3D(*a),
        Point3D(*b),
        Point3D(a[0] + up[0], a[1] + up[1], a[2] + up[2]),
    )


@register_loader
class ExampleForeignLoader:
    """Loads the illustrative ``example.timberframe`` schema."""

    schema = "example.timberframe"
    versions = ("1", "2", "*")

    def load(self, raw: dict[str, Any]) -> DetailDefinition:
        builder = (
            DetailBuilder()
            .named(raw["id"])
            .of_type(_SITUATIONS[raw["situation"]])
            .cover(_WALL_TYPES[raw["wall_type"]])
            .metadata(source_schema=self.schema)
        )
        for part in raw.get("parts", ()):
            role = _FUNCTIONS.get(part.get("function"))
            axis = _axis(part["line"])
            size = part["size"]
            if part["shape"] == "stick":
                builder.add_beam(RectSection(size["b"], size["h"]), axis, role=role)
            else:  # "board"
                builder.add_panel(PanelSection(size["b"], size["t"]), axis, role=role)
        return builder.build()

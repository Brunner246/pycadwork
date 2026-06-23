"""VisualizationAdapter: element visual state (color, ...).

Wraps cwapi3d's ``visualization_controller``. Element color is a visualization
concern, not an attribute — it does not live on ``attribute_controller`` — so it
gets its own sub-adapter here rather than sitting on ``AttributesAdapter``.

Adding a new visual property means three steps:
  1. Add the get/set pair here.
  2. Mirror it on ``FakeVisualizationAdapter`` in ``tests/_fakes/cadwork_adapter.py``.
  3. Expose it on the OOP layer (e.g. :class:`pycadwork.element.components.Attributes`).
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import ElementId


class VisualizationAdapter:
    """Read/write of element visual state — currently the cadwork color id."""

    def get_color(self, eid: ElementId) -> int:
        import visualization_controller

        return int(visualization_controller.get_color(eid))

    def set_color(self, eids: list[ElementId], color_id: int) -> None:
        import visualization_controller

        visualization_controller.set_color(list(eids), color_id)

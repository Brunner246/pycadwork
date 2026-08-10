"""CollisionAdapter: exact solid collision / contact / distance queries.

Wraps the cwapi3d calls pycadwork's geometric :mod:`pycadwork.connectivity`
layer deliberately approximates — these answer with the true solids, not their
bounding boxes. The three calls span two controllers (``element_controller``
for the boolean tests, ``geometry_controller`` for the metric one), grouped
here by responsibility just as :class:`ElementsAdapter` already spans
``element_controller`` and ``connector_axis_controller``.

Only the **pairwise** tests are wrapped; the bulk ``get_elements_in_*`` calls
are intentionally left out because :mod:`pycadwork.collision` does its own
spatial-index broad-phase and only ever asks about spatially-near pairs.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import ElementId


class CollisionAdapter:
    """Exact solid relationship queries on a pair of elements."""

    def are_in_collision(self, a: ElementId, b: ElementId) -> bool:
        """True if the two solids interpenetrate (share interior volume)."""
        import element_controller

        return bool(element_controller.check_if_elements_are_in_collision(a, b))

    def are_in_contact(self, a: ElementId, b: ElementId) -> bool:
        """True if the two solids touch or overlap (flush faces count)."""
        import element_controller

        return bool(element_controller.check_if_elements_are_in_contact(a, b))

    def minimum_distance(self, a: ElementId, b: ElementId) -> float:
        """The minimum distance between the two solids (``0.0`` if they touch)."""
        import geometry_controller

        return float(geometry_controller.get_minimum_distance_between_elements(a, b))

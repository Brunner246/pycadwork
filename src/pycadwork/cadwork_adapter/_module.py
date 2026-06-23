"""ModuleAdapter: the *only* code that touches the element-module surface.

This sub-adapter owns every call into ``cadwork.element_module_properties`` and
the ``element_controller`` module functions
(``set_element_module_properties_for_elements``,
``start_element_module_calculation[_silently]``, ``set_element_detail_path``).

The translation from the version-agnostic :class:`ModuleProperties` to the live
cwapi3d object runs through a **declarative setter table** — mirroring
``set_cover_kind``'s dict in ``_attributes.py``. The exact cwapi3d setter names
and arities live here and nowhere else; every call is ``hasattr``-guarded so a
leaner cwapi3d build silently skips a flag it lacks rather than raising.

.. note::

   The setter names below are the single place real cwapi3d names matter. They
   are confirmed against the live binding in the manual in-cadwork smoke test;
   adjust only this table if an arity differs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pycadwork.cadwork_adapter.types import ElementId

if TYPE_CHECKING:
    from pycadwork.detail.properties import Distribution, ModuleProperties


@dataclass(frozen=True, slots=True)
class _DistSetters:
    """The five cwapi3d setters backing one :class:`Distribution` axis."""

    active: str
    distance: str
    use_number: str
    number: str
    use_max_distance: str
    max_distance: str


# Independent boolean flags: (ModuleProperties attr, cwapi3d setter).
_BOOL_SETTERS: tuple[tuple[str, str], ...] = (
    ("stretch_with_top_of_wall", "set_stretch_with_top_of_wall"),
    ("stretch_with_bottom_of_wall", "set_stretch_with_bottom_of_wall"),
    ("move_with_top_of_wall", "set_move_with_top_of_wall"),
    ("move_with_bottom_of_wall", "set_move_with_bottom_of_wall"),
    ("auxiliary", "set_auxiliary"),
    ("not_cut_with_cutting_element", "set_not_cut_with_cutting_element"),
    ("solder_in_axis_direction", "set_solder_in_axis_direction"),
    ("no_collision_control", "set_no_collision_control"),
    ("no_inside_control", "set_no_inside_control"),
    ("use_for_detail_coordinate_system", "set_use_for_detail_coordinate_system"),
)

# Distribution axes: (ModuleProperties attr, the backing setters).
_DISTRIBUTIONS: tuple[tuple[str, _DistSetters], ...] = (
    (
        "distribute_in_axis",
        _DistSetters(
            active="set_distribute_in_axis_direction",
            distance="set_distribute_in_axis_direction_distance",
            use_number="set_distribute_in_axis_direction_use_number",
            number="set_distribute_in_axis_direction_number",
            use_max_distance="set_distribute_in_axis_direction_use_max_distance",
            max_distance="set_distribute_in_axis_direction_max_distance",
        ),
    ),
    (
        "distribute_perpendicular",
        _DistSetters(
            active="set_distribute_perpendicular_to_axis_direction",
            distance="set_distribute_perpendicular_to_axis_direction_distance",
            use_number="set_distribute_perpendicular_to_axis_direction_use_number",
            number="set_distribute_perpendicular_to_axis_direction_number",
            use_max_distance="set_distribute_perpendicular_to_axis_direction_use_max_distance",
            max_distance="set_distribute_perpendicular_to_axis_direction_max_distance",
        ),
    ),
)

# NamedFlag fields: (attr, active-setter, name-setter).
_NAMED_FLAGS: tuple[tuple[str, str, str], ...] = (
    ("unique_layername", "set_unique_layername", "set_layername"),
    (
        "keep_in_center_of_layer_current_wall",
        "set_keep_in_center_of_layer_current_wall",
        "set_keep_in_center_of_layer_current_wall_layername",
    ),
    (
        "keep_in_center_of_layer_neighbour_wall",
        "set_keep_in_center_of_layer_neighbour_wall",
        "set_keep_in_center_of_layer_neighbour_wall_layername",
    ),
)


class ModuleAdapter:
    """All element-module property and calculation access."""

    # ---- property translation ----

    @staticmethod
    def _call(props: Any, setter: str, value: Any) -> None:
        """Invoke ``props.<setter>(value)`` if the live object exposes it."""
        fn = getattr(props, setter, None)
        if fn is not None:
            fn(value)

    @classmethod
    def _apply_distribution(
        cls, props: Any, dist: "Distribution", setters: _DistSetters
    ) -> None:
        cls._call(props, setters.active, dist.active)
        if dist.count is not None:
            cls._call(props, setters.use_number, True)
            cls._call(props, setters.number, dist.count)
        elif dist.max_distance is not None:
            cls._call(props, setters.use_max_distance, True)
            cls._call(props, setters.max_distance, dist.max_distance)
        elif dist.distance is not None:
            cls._call(props, setters.distance, dist.distance)

    @classmethod
    def _apply_to(cls, props: Any, properties: "ModuleProperties") -> None:
        """Push every :class:`ModuleProperties` field onto a live props object."""
        for attr, setter in _BOOL_SETTERS:
            cls._call(props, setter, getattr(properties, attr))
        for attr, setters in _DISTRIBUTIONS:
            cls._apply_distribution(props, getattr(properties, attr), setters)
        cutting = properties.cutting_element
        cls._call(props, "set_cutting_element", cutting.active)
        if cutting.active and cutting.priority is not None:
            cls._call(props, "set_cutting_element_priority", cutting.priority)
        for attr, active_setter, name_setter in _NAMED_FLAGS:
            flag = getattr(properties, attr)
            cls._call(props, active_setter, flag.active)
            if flag.active and flag.name:
                cls._call(props, name_setter, flag.name)

    # ---- live calls ----

    def apply_properties(
        self, eids: list[ElementId], properties: "ModuleProperties"
    ) -> None:
        import cadwork
        import element_controller

        props = cadwork.element_module_properties()
        self._apply_to(props, properties)
        element_controller.set_element_module_properties_for_elements(list(eids), props)

    def start_calculation(self, cover_eids: list[ElementId]) -> None:
        import element_controller

        element_controller.start_element_module_calculation(list(cover_eids))

    def start_calculation_silently(self, cover_eids: list[ElementId]) -> None:
        import element_controller

        element_controller.start_element_module_calculation_silently(list(cover_eids))

    def set_detail_path(self, path: str) -> None:
        import element_controller

        element_controller.set_element_detail_path(path)

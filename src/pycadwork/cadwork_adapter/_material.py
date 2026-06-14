"""MaterialAdapter: read the project's material catalog from cwapi3d.

The only seam that touches ``material_controller``. It reads each material's
identity and structural properties into a :class:`MaterialSnapshot` — the stable
shape the rest of pycadwork sees — resolving a material from the *name* an
element carries (``attribute_controller.get_element_material_name`` →
``material_controller.get_material_id``).

Every property getter is probed with ``hasattr`` first: cwapi3d versions differ
in which material getters they expose, and pycadwork must stay agnostic of any
specific version (so a missing getter yields the field's default rather than an
``AttributeError``).
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import MaterialId, MaterialSnapshot


def _get_str(controller: object, name: str, material_id: MaterialId) -> str:
    """Call ``controller.<name>(material_id)`` if it exists, else ``""``."""
    getter = getattr(controller, name, None)
    return str(getter(material_id)) if getter is not None else ""


def _get_float(controller: object, name: str, material_id: MaterialId) -> float:
    """Call ``controller.<name>(material_id)`` if it exists, else ``0.0``."""
    getter = getattr(controller, name, None)
    return float(getter(material_id)) if getter is not None else 0.0


class MaterialAdapter:
    """Read access to the cadwork material catalog (identity + structural data)."""

    def get_all_material_ids(self) -> list[MaterialId]:
        import material_controller

        return [MaterialId(int(mid)) for mid in material_controller.get_all_materials()]

    def get_material_id(self, name: str) -> MaterialId:
        import material_controller

        return MaterialId(int(material_controller.get_material_id(name)))

    def get_material(self, material_id: MaterialId) -> MaterialSnapshot:
        import material_controller

        c = material_controller
        return MaterialSnapshot(
            name=_get_str(c, "get_name", material_id),
            group=_get_str(c, "get_group", material_id),
            code=_get_str(c, "get_code", material_id),
            grade=_get_str(c, "get_grade", material_id),
            quality=_get_str(c, "get_quality", material_id),
            modulus_elasticity_1=_get_float(c, "get_modulus_elasticity_1", material_id),
            modulus_elasticity_2=_get_float(c, "get_modulus_elasticity_2", material_id),
            modulus_elasticity_3=_get_float(c, "get_modulus_elasticity_3", material_id),
            shear_modulus_1=_get_float(c, "get_shear_modulus_1", material_id),
            shear_modulus_2=_get_float(c, "get_shear_modulus_2", material_id),
            weight=_get_float(c, "get_weight", material_id),
        )

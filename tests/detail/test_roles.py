"""Semantic roles resolve to property presets; explicit properties override them."""

from __future__ import annotations

import pytest

from pycadwork.detail.properties import ModuleProperties
from pycadwork.detail.roles import (
    UnknownRoleError,
    get_role,
    register_role,
    resolve,
    role_names,
)


def test_builtin_roles_are_registered():
    names = role_names()
    assert {"bottom_plate", "top_plate", "stud", "sheathing", "cutting_element"} <= set(
        names
    )


def test_get_role_returns_preset():
    role = get_role("cutting_element")
    assert role.properties.cutting_element.active


def test_unknown_role_raises():
    with pytest.raises(UnknownRoleError, match="unknown role"):
        get_role("no_such_role")


def test_register_role_adds_a_preset():
    @register_role("test_blocking")
    def _blocking() -> ModuleProperties:
        return ModuleProperties(no_collision_control=True)

    assert get_role("test_blocking").properties.no_collision_control


def test_resolve_prefers_explicit_properties_over_role():
    explicit = ModuleProperties(auxiliary=True)
    # 'stud' preset does not set auxiliary; the explicit value must win whole.
    assert resolve("stud", explicit) is explicit


def test_resolve_falls_back_to_role_then_default():
    assert resolve("stud", None) == get_role("stud").properties
    assert resolve(None, None) == ModuleProperties()

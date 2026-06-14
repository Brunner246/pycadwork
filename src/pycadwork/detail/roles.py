"""Semantic roles: named :class:`ModuleProperties` presets.

A detail author thinks in roles — *bottom plate*, *stud*, *sheathing*, *cutting
element* — not in raw property flags. A :class:`SemanticRole` binds such a name
to a ready-made :class:`ModuleProperties` value. A :class:`MemberSpec`'s ``role``
resolves to that preset; an explicit ``properties`` on the spec overrides it
entirely.

New roles register themselves at import via the :func:`register_role` decorator,
mirroring ``element/registry.py`` — so a downstream package can add its own
vocabulary without editing this module.
"""

from __future__ import annotations

from typing import Callable

from pycadwork.detail.properties import (
    CuttingElement,
    Distribution,
    ModuleProperties,
)


class UnknownRoleError(KeyError):
    """Raised when a role name is not registered."""


class SemanticRole:
    """A named preset over :class:`ModuleProperties`."""

    __slots__ = ("name", "properties")

    def __init__(self, name: str, properties: ModuleProperties) -> None:
        self.name = name
        self.properties = properties

    def __repr__(self) -> str:
        return f"SemanticRole(name={self.name!r})"


_REGISTRY: dict[str, SemanticRole] = {}


def register_role(name: str) -> Callable[[Callable[[], ModuleProperties]], SemanticRole]:
    """Decorator: register the decorated factory's result as role ``name``.

    The factory takes no arguments and returns the preset::

        @register_role("stud")
        def _stud() -> ModuleProperties:
            return ModuleProperties(distribute_in_axis=Distribution(active=True, distance=625))
    """

    def decorate(factory: Callable[[], ModuleProperties]) -> SemanticRole:
        role = SemanticRole(name, factory())
        _REGISTRY[name] = role
        return role

    return decorate


def get_role(name: str) -> SemanticRole:
    """Return the registered :class:`SemanticRole`, or raise :class:`UnknownRoleError`."""
    try:
        return _REGISTRY[name]
    except KeyError:
        raise UnknownRoleError(
            f"unknown role {name!r}; registered: {sorted(_REGISTRY)}"
        ) from None


def role_names() -> list[str]:
    """All registered role names, sorted."""
    return sorted(_REGISTRY)


def resolve(role: str | None, properties: ModuleProperties | None) -> ModuleProperties:
    """Resolve a member's effective properties.

    An explicit ``properties`` wins outright; otherwise a ``role`` resolves to
    its preset; with neither, the default (all-off) properties apply.
    """
    if properties is not None:
        return properties
    if role is not None:
        return get_role(role).properties
    return ModuleProperties()


# ---- built-in roles ----


@register_role("bottom_plate")
def _bottom_plate() -> ModuleProperties:
    return ModuleProperties(stretch_with_bottom_of_wall=True)


@register_role("top_plate")
def _top_plate() -> ModuleProperties:
    return ModuleProperties(stretch_with_top_of_wall=True)


@register_role("stud")
def _stud() -> ModuleProperties:
    return ModuleProperties(
        stretch_with_top_of_wall=True,
        stretch_with_bottom_of_wall=True,
        distribute_in_axis=Distribution(active=True, distance=625.0),
    )


@register_role("sheathing")
def _sheathing() -> ModuleProperties:
    return ModuleProperties(
        stretch_with_top_of_wall=True,
        stretch_with_bottom_of_wall=True,
    )


@register_role("cutting_element")
def _cutting_element() -> ModuleProperties:
    return ModuleProperties(cutting_element=CuttingElement(active=True, priority=1))

"""Built-in Then catalog and the process-global ``register_step`` registry.

Phrases are full-match regexes. Named groups are passed as kwargs to the
factory, which returns one :class:`~pycadwork.rules.engine.Rule` or a sequence.
Built-ins are registered the same way at import; :func:`reset_steps` restores
them.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import replace

from pycadwork.persistence.records import ElementRecord
from pycadwork.reporting.index import SnapshotIndex
from pycadwork.rules import (
    ElementRule,
    Rule,
    Selector,
    Severity,
    all_of,
    any_element,
    count_is,
    dimensions_within,
    for_types,
    ifc_type_is,
    material_is,
    named_equals,
)

Factory = Callable[..., Rule | Sequence[Rule]]

_CatalogEntry = tuple[re.Pattern[str], Factory]

_builtins: list[_CatalogEntry] = []
_catalog: list[_CatalogEntry] = []

_TYPE = r"(?P<element_type>\w+)"
_NAME = r'"(?P<name>[^"]*)"'
_MATERIAL = r'"(?P<material>[^"]*)"'
_IFC = r'"(?P<ifc>[^"]*)"'
_GROUP = r'"(?P<group>[^"]*)"'
_AXIS = r"(?P<axis>length|width|height)"
_VALUE = r"(?P<value>\d+(?:\.\d+)?)"
_LO = r"(?P<lo>\d+(?:\.\d+)?)"
_HI = r"(?P<hi>\d+(?:\.\d+)?)"
_N = r"(?P<n>\d+)"


def register_step(pattern: str, factory: Factory) -> None:
    """Register a Then/Given phrase.

    ``pattern`` is a full-match regex. Named groups are passed as kwargs to
    ``factory``. ``factory`` returns one ``Rule`` or a sequence. Registration
    is process-global; a test fixture should restore the catalog.
    """
    _catalog.insert(0, (re.compile(pattern), factory))


def reset_steps() -> None:
    """Restore the built-in catalog, dropping any :func:`register_step` extras."""
    _catalog[:] = list(_builtins)


def match_step(text: str) -> Rule | Sequence[Rule] | None:
    """Dispatch ``text`` through the catalog. ``None`` if no phrase matches."""
    for pattern, factory in _catalog:
        matched = pattern.fullmatch(text)
        if matched is not None:
            return factory(**matched.groupdict())
    return None


def _selects(element_type: str, name: str | None = None) -> Selector:
    if element_type == "element":
        selectors: list[Selector] = [any_element()]
    else:
        selectors = [for_types(element_type)]
    if name is not None:
        selectors.append(named_equals(name))
    if len(selectors) == 1:
        return selectors[0]
    return all_of(*selectors)


def _require_geometry(rule: ElementRule) -> ElementRule:
    inner = rule.check

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        if index.geometry(element.id) is None:
            return "no geometry"
        return inner(index, element)

    return replace(rule, check=check)


def _material(*, element_type: str, name: str, material: str) -> ElementRule:
    return material_is(material, selects=_selects(element_type, name), severity=Severity.ERROR)


def _ifc(*, element_type: str, name: str, ifc: str) -> ElementRule:
    return ifc_type_is(ifc, selects=_selects(element_type, name), severity=Severity.ERROR)


def _dimension(*, element_type: str, name: str, axis: str, value: str) -> ElementRule:
    amount = float(value)
    rule = dimensions_within(
        **{axis: (amount, amount)},  # type: ignore[arg-type]
        selects=_selects(element_type, name),
        severity=Severity.ERROR,
    )
    return _require_geometry(rule)


def _dimension_range(*, element_type: str, name: str, axis: str, lo: str, hi: str) -> ElementRule:
    rule = dimensions_within(
        **{axis: (float(lo), float(hi))},  # type: ignore[arg-type]
        selects=_selects(element_type, name),
        severity=Severity.ERROR,
    )
    return _require_geometry(rule)


def _group(*, element_type: str, name: str, group: str) -> ElementRule:
    selects = _selects(element_type, name)

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        attribute = index.attribute(element.id)
        actual = attribute.group_name if attribute else ""
        if actual == group:
            return None
        if not actual:
            return "no group"
        return f"group {actual!r} is not {group!r}"

    return ElementRule(
        id="group-is",
        description="element group must match",
        severity=Severity.ERROR,
        selects=selects,
        check=check,
    )


def _count_named(*, n: str, element_type: str, name: str) -> Rule:
    return count_is(int(n), selects=_selects(element_type, name), severity=Severity.ERROR)


def _count_type(*, n: str, element_type: str) -> Rule:
    return count_is(int(n), selects=_selects(element_type), severity=Severity.ERROR)


def _register_builtin(pattern: str, factory: Factory) -> None:
    entry = (re.compile(pattern), factory)
    _builtins.append(entry)
    _catalog.append(entry)


def _install_builtins() -> None:
    # More specific phrases first so "between" wins over exact dimension,
    # and "named" counts win over type-only counts.
    _register_builtin(
        rf"every {_TYPE} named {_NAME} has {_AXIS} between {_LO} and {_HI}",
        _dimension_range,
    )
    _register_builtin(
        rf"every {_TYPE} named {_NAME} has {_AXIS} {_VALUE}",
        _dimension,
    )
    _register_builtin(
        rf"every {_TYPE} named {_NAME} has material {_MATERIAL}",
        _material,
    )
    _register_builtin(
        rf"every {_TYPE} named {_NAME} has ifc type {_IFC}",
        _ifc,
    )
    _register_builtin(
        rf"every {_TYPE} named {_NAME} has group {_GROUP}",
        _group,
    )
    _register_builtin(
        rf"there are {_N} {_TYPE}s named {_NAME}",
        _count_named,
    )
    _register_builtin(
        rf"there are {_N} {_TYPE}s",
        _count_type,
    )


_install_builtins()

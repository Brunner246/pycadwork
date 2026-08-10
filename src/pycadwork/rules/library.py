"""Built-in rules — factory functions returning a ready-to-run :class:`Rule`.

Each factory is a module-level free function (like reporting's ``by_*`` axes),
so a rule set is just a list of calls::

    from pycadwork.rules import check, has_material, dimensions_within

    report = check(snapshot, [has_material(), dimensions_within(width=(40, 300))])

Every rule reads **only** fields the snapshot actually carries. Element rules
accept a ``selects=`` override to narrow their scope and a ``severity=``
override; model rules accept ``severity=``. A custom rule needs no factory here
— construct an :class:`ElementRule` / :class:`ModelRule` directly.

One check is deliberately *absent*: a true point-to-point minimum spacing
between drillings. The snapshot stores only an axis-aligned bounding box and the
three axis points per element, not the drilling geometry that an honest spacing
test needs — so it would give false confidence. Write it as a custom
:class:`ModelRule` over the geometry you trust when you need it.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable

from pycadwork.persistence._ids import ElementId
from pycadwork.persistence.records import ElementRecord, ModelSnapshot
from pycadwork.reporting.index import SnapshotIndex
from pycadwork.rules.engine import (
    ElementRule,
    ModelFinding,
    ModelRule,
    Selector,
    for_types,
)
from pycadwork.rules.severity import Severity

#: The fields :func:`naming_matches` can test.
_NAME_FIELDS = ("name", "group_name", "subgroup")


# ---- element rules ----


def has_material(
    *, severity: Severity = Severity.WARNING, selects: Selector | None = None
) -> ElementRule:
    """Fail any element whose ``material_name`` is empty."""

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        attribute = index.attribute(element.id)
        if attribute is not None and attribute.material_name:
            return None
        return "no material assigned"

    return ElementRule(
        id="has-material",
        description="element must have a material",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def named(
    *, severity: Severity = Severity.WARNING, selects: Selector | None = None
) -> ElementRule:
    """Fail any element whose ``name`` is empty."""

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        attribute = index.attribute(element.id)
        if attribute is not None and attribute.name:
            return None
        return "no name"

    return ElementRule(
        id="named",
        description="element must have a name",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def has_production_number(
    *, severity: Severity = Severity.INFO, selects: Selector | None = None
) -> ElementRule:
    """Fail any element whose ``production_number`` is not positive."""

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        attribute = index.attribute(element.id)
        if attribute is not None and attribute.production_number > 0:
            return None
        return "no production number"

    return ElementRule(
        id="has-production-number",
        description="element must carry a production number",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def assigned_to_storey(
    *, severity: Severity = Severity.WARNING, selects: Selector | None = None
) -> ElementRule:
    """Fail any element with no storey assignment in the snapshot."""

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        return (
            None
            if index.assignment(element.id) is not None
            else "not assigned to a storey"
        )

    return ElementRule(
        id="assigned-to-storey",
        description="element must be assigned to a storey",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def material_in(
    allowed: Iterable[str],
    *,
    severity: Severity = Severity.ERROR,
    selects: Selector | None = None,
) -> ElementRule:
    """Fail any element whose material is not in ``allowed`` (empty material passes)."""
    permitted = frozenset(allowed)

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        attribute = index.attribute(element.id)
        material = attribute.material_name if attribute else ""
        if not material or material in permitted:
            return None
        return f"material {material!r} not in the allowed set"

    return ElementRule(
        id="material-in",
        description="element material must be one of the allowed materials",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def naming_matches(
    pattern: str,
    *,
    field: str = "name",
    severity: Severity = Severity.WARNING,
    selects: Selector | None = None,
) -> ElementRule:
    """Fail any element whose ``field`` does not fully match ``pattern``.

    ``field`` is one of ``"name"`` / ``"group_name"`` / ``"subgroup"``. An empty
    value fails (it cannot match a convention); use a pattern like ``r".*"`` or
    a narrower ``selects`` if empties should be tolerated.
    """
    if field not in _NAME_FIELDS:
        raise ValueError(f"field must be one of {_NAME_FIELDS}, got {field!r}")
    compiled = re.compile(pattern)

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        attribute = index.attribute(element.id)
        value = getattr(attribute, field) if attribute else ""
        if value and compiled.fullmatch(value):
            return None
        return f"{field}={value!r} does not match {pattern!r}"

    return ElementRule(
        id="naming-matches",
        description="element field must match the naming convention",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def dimensions_within(
    *,
    length: tuple[float, float] | None = None,
    width: tuple[float, float] | None = None,
    height: tuple[float, float] | None = None,
    severity: Severity = Severity.ERROR,
    selects: Selector | None = None,
) -> ElementRule:
    """Fail an element whose length/width/height falls outside the given range(s).

    Only the axes you pass are checked. Selects beams and plates by default and
    skips an element with no geometry satellite (no false failure on missing
    data — gate elsewhere if absence should itself fail).
    """
    bounds = {
        k: v for k, v in (("length", length), ("width", width), ("height", height)) if v
    }

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        geometry = index.geometry(element.id)
        if geometry is None:
            return None
        for axis, (low, high) in bounds.items():
            value = getattr(geometry, axis)
            if not (low <= value <= high):
                return f"{axis}={value:g} outside [{low:g}, {high:g}]"
        return None

    return ElementRule(
        id="dimensions-within",
        description="element dimensions must be within range",
        severity=severity,
        selects=selects or for_types("beam", "plate"),
        check=check,
    )


def volume_between(
    minimum: float,
    maximum: float,
    *,
    severity: Severity = Severity.WARNING,
    selects: Selector | None = None,
) -> ElementRule:
    """Fail an element whose volume falls outside ``[minimum, maximum]``."""

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        geometry = index.geometry(element.id)
        if geometry is None:
            return None
        if minimum <= geometry.volume <= maximum:
            return None
        return f"volume={geometry.volume:g} outside [{minimum:g}, {maximum:g}]"

    return ElementRule(
        id="volume-between",
        description="element volume must be within range",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


def weight_between(
    minimum: float,
    maximum: float,
    *,
    severity: Severity = Severity.INFO,
    selects: Selector | None = None,
) -> ElementRule:
    """Fail an element whose weight falls outside ``[minimum, maximum]``."""

    def check(index: SnapshotIndex, element: ElementRecord) -> str | None:
        geometry = index.geometry(element.id)
        if geometry is None:
            return None
        if minimum <= geometry.weight <= maximum:
            return None
        return f"weight={geometry.weight:g} outside [{minimum:g}, {maximum:g}]"

    return ElementRule(
        id="weight-between",
        description="element weight must be within range",
        severity=severity,
        selects=selects or _default_parts(),
        check=check,
    )


# ---- model rules ----


def material_is_known(*, severity: Severity = Severity.ERROR) -> ModelRule:
    """Fail an element carrying a material name with no master row in the catalog.

    A model rule rather than an element rule: it cross-references each element's
    material against the snapshot's deduplicated ``material`` master, which a
    per-element predicate cannot see. An element with no material passes.
    """

    def evaluate(
        index: SnapshotIndex, snapshot: ModelSnapshot
    ) -> Iterable[ModelFinding]:
        known = snapshot.materials_by_name()
        findings: list[ModelFinding] = []
        for element in sorted(snapshot.elements, key=lambda e: int(e.id)):
            attribute = index.attribute(element.id)
            material = attribute.material_name if attribute else ""
            if material and material not in known:
                findings.append(
                    ModelFinding(
                        element.id, f"material {material!r} has no catalog entry"
                    )
                )
        return findings

    return ModelRule(
        id="material-is-known",
        description="element material must exist in the project catalog",
        severity=severity,
        evaluate=evaluate,
    )


def no_duplicate_part_numbers_with_different_dims(
    *, severity: Severity = Severity.ERROR, precision: int = 1
) -> ModelRule:
    """Fail when one ``part_number`` is shared by parts of different size.

    Two elements may legitimately share a part number only if they are the same
    part — same length/width/height (rounded to ``precision``). When a part
    number's bucket holds more than one distinct size, every element in that
    bucket is reported.
    """

    def evaluate(
        index: SnapshotIndex, snapshot: ModelSnapshot
    ) -> Iterable[ModelFinding]:
        buckets: dict[str, list[tuple[ElementId, tuple[float, float, float]]]] = (
            defaultdict(list)
        )
        for element in snapshot.elements:
            attribute = index.attribute(element.id)
            geometry = index.geometry(element.id)
            if attribute is None or geometry is None or not attribute.part_number:
                continue
            # Coerce to float before rounding: a live backend may hand back an
            # int dimension while a SQL round-trip yields a float, and
            # ``round(int, n)`` stays int — which would make the same part read
            # differently from the two sources. Float keeps the report equal.
            dims = (
                round(float(geometry.length), precision),
                round(float(geometry.width), precision),
                round(float(geometry.height), precision),
            )
            buckets[attribute.part_number].append((element.id, dims))

        findings: list[ModelFinding] = []
        for part_number in sorted(buckets):
            members = buckets[part_number]
            distinct = {dims for _, dims in members}
            if len(distinct) <= 1:
                continue
            for eid, dims in sorted(members, key=lambda m: int(m[0])):
                findings.append(
                    ModelFinding(
                        eid, f"part number {part_number!r} also used for size {dims}"
                    )
                )
        return findings

    return ModelRule(
        id="no-duplicate-part-numbers",
        description="a part number must denote a single size",
        severity=severity,
        evaluate=evaluate,
    )


def unique_assembly_numbers(*, severity: Severity = Severity.WARNING) -> ModelRule:
    """Fail when one ``assembly_number`` spans inconsistent name or material.

    An assembly should be homogeneous: every element sharing an assembly number
    is expected to carry the same name and material. A bucket mixing names or
    materials reports each of its elements.
    """

    def evaluate(
        index: SnapshotIndex, snapshot: ModelSnapshot
    ) -> Iterable[ModelFinding]:
        buckets: dict[str, list[tuple[ElementId, str, str]]] = defaultdict(list)
        for element in snapshot.elements:
            attribute = index.attribute(element.id)
            if attribute is None or not attribute.assembly_number:
                continue
            buckets[attribute.assembly_number].append(
                (element.id, attribute.name, attribute.material_name)
            )

        findings: list[ModelFinding] = []
        for number in sorted(buckets):
            members = buckets[number]
            names = {name for _, name, _ in members}
            materials = {material for _, _, material in members}
            if len(names) <= 1 and len(materials) <= 1:
                continue
            for eid, _, _ in sorted(members, key=lambda m: int(m[0])):
                findings.append(
                    ModelFinding(eid, f"assembly {number!r} mixes names/materials")
                )
        return findings

    return ModelRule(
        id="unique-assembly-numbers",
        description="an assembly number must denote one homogeneous assembly",
        severity=severity,
        evaluate=evaluate,
    )


def every_member_has_container_parent(
    *, severity: Severity = Severity.INFO
) -> ModelRule:
    """Fail an element flagged with a container parent that no link confirms.

    Cross-checks each element's ``parent_container_id`` against the
    ``container_member`` links: an element naming a parent that lists no matching
    member row is a dangling reference.
    """

    def evaluate(
        index: SnapshotIndex, snapshot: ModelSnapshot
    ) -> Iterable[ModelFinding]:
        members_by_container = snapshot.members_by_container()
        findings: list[ModelFinding] = []
        for element in sorted(snapshot.elements, key=lambda e: int(e.id)):
            parent = element.parent_container_id
            if parent is None:
                continue
            if element.id not in members_by_container.get(parent, []):
                findings.append(
                    ModelFinding(
                        element.id,
                        f"names container {int(parent)} but is not its member",
                    )
                )
        return findings

    return ModelRule(
        id="member-has-container-parent",
        description="a container parent reference must be confirmed by a member link",
        severity=severity,
        evaluate=evaluate,
    )


# ---- shared default selector ----


def _default_parts() -> Selector:
    """The default element-rule scope: the path-anchored stock (beams/plates/MEP)."""
    return for_types("beam", "plate", "circularmep", "rectangularmep")

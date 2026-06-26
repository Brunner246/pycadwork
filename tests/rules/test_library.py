"""Built-in rules: each factory passes the good case and flags the bad one."""

from __future__ import annotations

from pycadwork.persistence.records import (
    AttributeRecord,
    ContainerMemberRecord,
    ElementRecord,
    GeometryRecord,
    MaterialRecord,
    ModelSnapshot,
    ProjectRecord,
    StoreyAssignmentRecord,
)
from pycadwork.rules import (
    Severity,
    any_element,
    assigned_to_storey,
    check,
    dimensions_within,
    every_member_has_container_parent,
    has_material,
    has_production_number,
    material_in,
    material_is_known,
    named,
    naming_matches,
    no_duplicate_part_numbers_with_different_dims,
    unique_assembly_numbers,
    volume_between,
)


def _snapshot(**kwargs: object) -> ModelSnapshot:
    return ModelSnapshot(project=ProjectRecord("g"), **kwargs)  # type: ignore[arg-type]


def failed_ids(report) -> list[int]:
    return [v.element_id for v in report.violations]


def test_has_material() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        attributes=(
            AttributeRecord("g", 1, material_name="Pine"),
            AttributeRecord("g", 2, material_name=""),
        ),
    )
    assert failed_ids(check(snap, [has_material()])) == [2]


def test_named() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        attributes=(
            AttributeRecord("g", 1, name="Stud"),
            AttributeRecord("g", 2, name=""),
        ),
    )
    assert failed_ids(check(snap, [named()])) == [
        2
    ]  # the element with no material (id 2) was flagged


def test_has_production_number() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        attributes=(
            AttributeRecord("g", 1, production_number=5),
            AttributeRecord("g", 2, production_number=0),
        ),
    )
    assert failed_ids(check(snap, [has_production_number()])) == [2]


def test_assigned_to_storey() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        storey_assignments=(StoreyAssignmentRecord("g", 1, "B", "GF"),),
    )
    assert failed_ids(check(snap, [assigned_to_storey()])) == [2]


def test_material_in_allows_empty_and_flags_disallowed() -> None:
    snap = _snapshot(
        elements=(
            ElementRecord("g", 1, "beam"),
            ElementRecord("g", 2, "beam"),
            ElementRecord("g", 3, "beam"),
        ),
        attributes=(
            AttributeRecord("g", 1, material_name="Pine"),
            AttributeRecord("g", 2, material_name="Concrete"),
            AttributeRecord("g", 3, material_name=""),  # empty passes
        ),
    )
    assert failed_ids(check(snap, [material_in({"Pine", "Spruce"})])) == [2]


def test_naming_matches_flags_mismatch_and_empty() -> None:
    snap = _snapshot(
        elements=(
            ElementRecord("g", 1, "beam"),
            ElementRecord("g", 2, "beam"),
            ElementRecord("g", 3, "beam"),
        ),
        attributes=(
            AttributeRecord("g", 1, name="ST-001"),
            AttributeRecord("g", 2, name="bad"),
            AttributeRecord("g", 3, name=""),
        ),
    )
    assert failed_ids(check(snap, [naming_matches(r"ST-\d+")])) == [2, 3]


def test_dimensions_within_skips_missing_geometry() -> None:
    snap = _snapshot(
        elements=(
            ElementRecord("g", 1, "beam"),
            ElementRecord("g", 2, "beam"),
            ElementRecord("g", 3, "beam"),  # no geometry satellite
        ),
        geometries=(
            GeometryRecord("g", 1, width=100.0),
            GeometryRecord("g", 2, width=900.0),
        ),
    )
    assert failed_ids(check(snap, [dimensions_within(width=(40.0, 400.0))])) == [2]


def test_volume_between() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        geometries=(
            GeometryRecord("g", 1, volume=0.05),
            GeometryRecord("g", 2, volume=5.0),
        ),
    )
    assert failed_ids(check(snap, [volume_between(0.0, 1.0)])) == [2]


def test_material_is_known_model_rule() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        attributes=(
            AttributeRecord("g", 1, material_name="Pine"),
            AttributeRecord("g", 2, material_name="Unobtainium"),
        ),
        materials=(MaterialRecord("g", "Pine"),),
    )
    report = check(snap, [material_is_known()])
    assert failed_ids(report) == [2]
    assert report.violations[0].severity is Severity.ERROR


def test_no_duplicate_part_numbers_flags_all_in_a_mixed_bucket() -> None:
    snap = _snapshot(
        elements=(
            ElementRecord("g", 1, "beam"),
            ElementRecord("g", 2, "beam"),
            ElementRecord("g", 3, "beam"),
        ),
        attributes=(
            AttributeRecord("g", 1, part_number="P1"),
            AttributeRecord("g", 2, part_number="P1"),
            AttributeRecord("g", 3, part_number="P2"),  # alone in its bucket
        ),
        geometries=(
            GeometryRecord("g", 1, length=3000.0, width=80.0, height=200.0),
            GeometryRecord(
                "g", 2, length=2000.0, width=80.0, height=200.0
            ),  # different size
            GeometryRecord("g", 3, length=1000.0),
        ),
    )
    assert failed_ids(
        check(snap, [no_duplicate_part_numbers_with_different_dims()])
    ) == [
        1,
        2,
    ]


def test_no_duplicate_part_numbers_passes_when_sizes_match() -> None:
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "beam"), ElementRecord("g", 2, "beam")),
        attributes=(
            AttributeRecord("g", 1, part_number="P1"),
            AttributeRecord("g", 2, part_number="P1"),
        ),
        geometries=(
            GeometryRecord("g", 1, length=3000.0, width=80.0, height=200.0),
            GeometryRecord("g", 2, length=3000.0, width=80.0, height=200.0),
        ),
    )
    assert (
        check(snap, [no_duplicate_part_numbers_with_different_dims()]).violations == ()
    )


def test_unique_assembly_numbers_flags_inconsistent_bucket() -> None:
    snap = _snapshot(
        elements=(
            ElementRecord("g", 1, "beam"),
            ElementRecord("g", 2, "beam"),
            ElementRecord("g", 3, "beam"),
        ),
        attributes=(
            AttributeRecord("g", 1, name="A", assembly_number="ASM1"),
            AttributeRecord("g", 2, name="B", assembly_number="ASM1"),  # mixes names
            AttributeRecord(
                "g", 3, name="C", assembly_number="ASM2"
            ),  # consistent alone
        ),
    )
    assert failed_ids(check(snap, [unique_assembly_numbers()])) == [1, 2]


def test_every_member_has_container_parent() -> None:
    snap = _snapshot(
        elements=(
            ElementRecord("g", 1, "beam", parent_container_id=10),  # confirmed
            ElementRecord("g", 2, "beam", parent_container_id=10),  # dangling
            ElementRecord("g", 3, "beam"),  # no parent claim
        ),
        container_members=(ContainerMemberRecord("g", 10, 1),),
    )
    assert failed_ids(check(snap, [every_member_has_container_parent()])) == [2]


def test_selects_override_widens_scope() -> None:
    # has_material defaults to parts; a node is normally out of scope.
    snap = _snapshot(
        elements=(ElementRecord("g", 1, "node"),),
        attributes=(AttributeRecord("g", 1, material_name=""),),
    )
    assert check(snap, [has_material()]).violations == ()
    assert failed_ids(check(snap, [has_material(selects=any_element())])) == [1]

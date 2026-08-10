"""Pure unit tests for :mod:`pycadwork.versioning._sync`.

No cadwork, no git — :func:`classify` / :func:`fingerprint_snapshot` are
exercised directly against hand-built :class:`ModelSnapshot` objects.
"""

from __future__ import annotations

from pycadwork.persistence import (
    CadworkGuid,
    ContainerId,
    ContainerMemberRecord,
    ElementId,
    ElementRecord,
    GeometryRecord,
    MemberId,
    ModelSnapshot,
    ProjectGuid,
    ProjectRecord,
)
from pycadwork.versioning._sync import classify, fingerprint_snapshot

_GUID = ProjectGuid("proj")

_Pair = tuple[ElementRecord, GeometryRecord]


def _beam(eid: int, guid: str, width: float = 80.0) -> _Pair:
    return (
        ElementRecord(_GUID, ElementId(eid), "beam", cadwork_guid=CadworkGuid(guid)),
        GeometryRecord(_GUID, ElementId(eid), width=width),
    )


def _container(eid: int, guid: str) -> _Pair:
    return (
        ElementRecord(
            _GUID, ElementId(eid), "container", cadwork_guid=CadworkGuid(guid)
        ),
        GeometryRecord(_GUID, ElementId(eid)),
    )


def _snapshot(
    *pairs: _Pair, container_members: tuple[ContainerMemberRecord, ...] = ()
) -> ModelSnapshot:
    return ModelSnapshot(
        project=ProjectRecord(_GUID),
        elements=tuple(p[0] for p in pairs),
        geometries=tuple(p[1] for p in pairs),
        container_members=container_members,
    )


# ---- classify: the basic cases ----


def test_unchanged_elements_are_left_untouched() -> None:
    a, b = _beam(1, "g1", 80.0), _beam(2, "g2", 200.0)
    current = _snapshot(a, b)
    target = _snapshot(a, b)

    plan = classify(current, target)

    assert plan.unchanged == (1, 2)
    assert plan.stale == ()
    assert plan.missing == ()


def test_changed_element_is_stale_and_its_new_content_is_missing() -> None:
    current = _snapshot(_beam(1, "g1", 80.0))
    target = _snapshot(_beam(1, "g1", 999.0))

    plan = classify(current, target)

    assert plan.unchanged == ()
    assert plan.stale == (1,)
    assert len(plan.missing) == 1


def test_removed_element_is_stale_with_nothing_missing() -> None:
    current = _snapshot(_beam(1, "g1"))
    target = _snapshot()

    plan = classify(current, target)

    assert plan.unchanged == ()
    assert plan.stale == (1,)
    assert plan.missing == ()


def test_new_target_element_is_missing_with_nothing_stale() -> None:
    current = _snapshot()
    target = _snapshot(_beam(1, "g1"))

    plan = classify(current, target)

    assert plan.unchanged == ()
    assert plan.stale == ()
    assert len(plan.missing) == 1


def test_duplicate_content_matches_via_multiset_even_with_different_guids() -> None:
    """A GUID history broken by an earlier smart-switch still reconciles by content."""
    current = _snapshot(_beam(1, "g1", 80.0), _beam(2, "g2", 80.0))
    target = _snapshot(_beam(1, "g3", 80.0), _beam(2, "g4", 80.0))

    plan = classify(current, target)

    assert set(plan.unchanged) == {1, 2}
    assert plan.stale == ()
    assert plan.missing == ()


# ---- container atomicity ----


def _container_snapshot(member2_width: float) -> ModelSnapshot:
    return _snapshot(
        _beam(1, "m1", 80.0),
        _beam(2, "m2", member2_width),
        _container(10, "c1"),
        container_members=(
            ContainerMemberRecord(_GUID, ContainerId(10), MemberId(1)),
            ContainerMemberRecord(_GUID, ContainerId(10), MemberId(2)),
        ),
    )


def test_container_fingerprint_folds_in_member_fingerprints() -> None:
    before = fingerprint_snapshot(_container_snapshot(120.0))
    after = fingerprint_snapshot(_container_snapshot(999.0))

    assert before[2] != after[2]  # the changed member's own fingerprint differs
    assert before[1] == after[1]  # the untouched sibling is unaffected on its own
    # ...yet the container's own fingerprint differs too: it is atomic.
    assert before[10] != after[10]


def test_classify_treats_a_changed_container_as_one_atomic_unit() -> None:
    current = _container_snapshot(120.0)
    target = _container_snapshot(999.0)

    plan = classify(current, target)

    # The whole group -- container plus the *individually unchanged* sibling
    # member -- is re-brought-in together: a container is atomic for change
    # detection, not just the member that actually changed.
    assert plan.unchanged == ()
    assert set(plan.stale) == {1, 2, 10}
    assert len(plan.missing) == 3


def test_classify_leaves_an_unaffected_container_and_its_members_alone() -> None:
    plan = classify(_container_snapshot(120.0), _container_snapshot(120.0))

    assert set(plan.unchanged) == {1, 2, 10}
    assert plan.stale == ()
    assert plan.missing == ()

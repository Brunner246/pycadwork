"""ModuleProperties and its grouped parts reject contradictory states.

The whole point of the grouped sub-dataclasses is that an instance which exists
is legal. These tests pin the invariants that enforce that.
"""

from __future__ import annotations

import pytest

from pycadwork.detail.properties import (
    CuttingElement,
    Distribution,
    ModuleProperties,
    ModulePropertyError,
    NamedFlag,
)


def test_distribution_off_by_default():
    d = Distribution()
    assert not d.active
    assert d.to_dict() == {"active": False}


def test_distribution_accepts_exactly_one_mode():
    assert Distribution(active=True, distance=625.0).distance == 625.0
    assert Distribution(active=True, count=4).count == 4
    assert Distribution(active=True, max_distance=800.0).max_distance == 800.0


def test_distribution_rejects_two_modes():
    with pytest.raises(ModulePropertyError, match="at most one"):
        Distribution(active=True, distance=625.0, count=4)


def test_distribution_active_requires_a_mode():
    with pytest.raises(ModulePropertyError, match="exactly one"):
        Distribution(active=True)


def test_distribution_inactive_rejects_a_mode():
    with pytest.raises(ModulePropertyError, match="inactive"):
        Distribution(active=False, distance=625.0)


def test_distribution_count_must_be_positive():
    with pytest.raises(ModulePropertyError, match="positive"):
        Distribution(active=True, count=0)


def test_cutting_element_priority_requires_active():
    with pytest.raises(ModulePropertyError, match="inactive"):
        CuttingElement(active=False, priority=3)


def test_cutting_element_priority_non_negative():
    with pytest.raises(ModulePropertyError, match=">= 0"):
        CuttingElement(active=True, priority=-1)


def test_named_flag_name_requires_active():
    with pytest.raises(ModulePropertyError, match="inactive"):
        NamedFlag(active=False, name="LAYER")


def test_module_properties_rejects_cut_and_not_cut():
    with pytest.raises(ModulePropertyError, match="cutting_element"):
        ModuleProperties(
            cutting_element=CuttingElement(active=True),
            not_cut_with_cutting_element=True,
        )


def test_module_properties_with_returns_edited_copy():
    base = ModuleProperties()
    edited = base.with_(auxiliary=True)
    assert edited.auxiliary
    assert not base.auxiliary  # original untouched
    assert edited != base


def test_module_properties_is_hashable():
    # Realizer batches members by their properties value in a dict.
    a = ModuleProperties(auxiliary=True)
    b = ModuleProperties(auxiliary=True)
    assert hash(a) == hash(b)
    assert len({a, b}) == 1

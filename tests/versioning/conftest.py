"""Shared fixtures for the versioning tests: a fake repo and a sample snapshot."""

from __future__ import annotations

from pathlib import Path

import pytest

from pycadwork.persistence.records import (
    AttributeRecord,
    ElementRecord,
    GeometryRecord,
    ModelSnapshot,
    ProjectRecord,
)
from tests._fakes.repository import FakeRepository

GUID = "proj-guid-1"


@pytest.fixture
def fake_repo(tmp_path: Path) -> FakeRepository:
    """A fresh working-tree-backed fake repository under ``tmp_path/repo``."""
    return FakeRepository(tmp_path / "repo")


@pytest.fixture
def sample_snapshot() -> ModelSnapshot:
    """A small two-element snapshot for codec/repository round-trips."""
    return ModelSnapshot(
        project=ProjectRecord(GUID, name="Tower"),
        elements=(
            ElementRecord(GUID, 1, "beam", cadwork_guid="g1"),
            ElementRecord(GUID, 2, "plate", cadwork_guid="g2"),
        ),
        attributes=(AttributeRecord(GUID, 1, name="Joist"),),
        geometries=(GeometryRecord(GUID, 1, length=3000.0, width=80.0, height=200.0),),
    )

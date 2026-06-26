"""Pure round-trip / determinism / edge-case tests for :class:`SnapshotCodec`.

These build snapshots from record literals — no cadwork, no git — so they run
anywhere. They pin the three properties the versioning bridge leans on: a
lossless round-trip, byte-identical output for equal (or reordered) snapshots,
and a loud failure on a malformed / conflicted tree.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from pycadwork.persistence.records import (
    AttributeRecord,
    BuildingRecord,
    ContainerMemberRecord,
    CoverRecord,
    ElementMaterialRecord,
    ElementRecord,
    GeometryRecord,
    MaterialRecord,
    ModelSnapshot,
    ProjectRecord,
    StoreyAssignmentRecord,
    StoreyRecord,
    UserAttributeRecord,
)
from pycadwork.versioning._codec import (
    FORMAT_VERSION,
    MANIFEST_FILE,
    MODEL_DIR,
    TABLE_SPECS,
    CodecError,
    SnapshotCodec,
)

GUID = "proj-guid-1"


def _populated_snapshot() -> ModelSnapshot:
    """A snapshot touching every table, with the tricky values pinned below."""
    return ModelSnapshot(
        project=ProjectRecord(GUID, name="Tower", latitude=47.05, longitude=8.31),
        elements=(
            ElementRecord(GUID, 1, "container", cadwork_guid="g1"),
            ElementRecord(GUID, 2, "plate", cadwork_guid="g2", parent_container_id=1),
            ElementRecord(GUID, 3, "beam", cadwork_guid="g3", parent_container_id=None),
        ),
        attributes=(
            AttributeRecord(GUID, 1, name="Box", group_name="A"),
            AttributeRecord(GUID, 3, name="Joist", production_number=7),
        ),
        geometries=(
            GeometryRecord(GUID, 3, p1x=0.1, length=2999.9999999999995, volume=1e-9),
        ),
        user_attributes=(
            UserAttributeRecord(GUID, 3, 1, value="a"),
            UserAttributeRecord(GUID, 3, 2, value="b"),
        ),
        covers=(CoverRecord(GUID, 1, "wall"),),
        container_members=(ContainerMemberRecord(GUID, 1, 2),),
        buildings=(BuildingRecord(GUID, "Haus"),),
        storeys=(StoreyRecord(GUID, "Haus", "EG", elevation=0.0),),
        storey_assignments=(
            StoreyAssignmentRecord(GUID, 1, "Haus", "EG", spans=False),
            StoreyAssignmentRecord(GUID, 3, "Haus", "EG", spans=True),
        ),
        materials=(MaterialRecord(GUID, "GL24h", grade="GL24h", weight=470.0),),
        element_materials=(
            ElementMaterialRecord(GUID, 3, cadwork_guid="g3", material_name="GL24h"),
        ),
    )


def _empty_snapshot() -> ModelSnapshot:
    return ModelSnapshot(project=ProjectRecord(GUID))


# ---- round-trip ----


def test_round_trip_populated(tmp_path: Path) -> None:
    snap = _populated_snapshot()
    SnapshotCodec().write(snap, tmp_path)
    assert SnapshotCodec().read(tmp_path) == snap


def test_round_trip_empty(tmp_path: Path) -> None:
    snap = _empty_snapshot()
    SnapshotCodec().write(snap, tmp_path)
    assert SnapshotCodec().read(tmp_path) == snap


def test_missing_project_file_defaults_from_manifest(tmp_path: Path) -> None:
    SnapshotCodec().write(_empty_snapshot(), tmp_path)
    (tmp_path / MODEL_DIR / "project.jsonl").unlink()
    restored = SnapshotCodec().read(tmp_path)
    assert restored.project == ProjectRecord(GUID)


# ---- determinism ----


def test_byte_identical_for_equal_snapshots(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    SnapshotCodec().write(_populated_snapshot(), a)
    SnapshotCodec().write(_populated_snapshot(), b)
    for spec in TABLE_SPECS:
        rel = Path(MODEL_DIR) / spec.filename
        assert (a / rel).read_bytes() == (b / rel).read_bytes()


def test_byte_identical_regardless_of_input_order(tmp_path: Path) -> None:
    snap = _populated_snapshot()
    reordered = dataclasses.replace(
        snap,
        elements=tuple(reversed(snap.elements)),
        user_attributes=tuple(reversed(snap.user_attributes)),
        storey_assignments=tuple(reversed(snap.storey_assignments)),
    )
    a, b = tmp_path / "a", tmp_path / "b"
    SnapshotCodec().write(snap, a)
    SnapshotCodec().write(reordered, b)
    element_file = Path(MODEL_DIR) / "element.jsonl"
    assert (a / element_file).read_bytes() == (b / element_file).read_bytes()


def test_records_sorted_by_primary_key(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    lines = (tmp_path / MODEL_DIR / "element.jsonl").read_text().splitlines()
    ids = [json.loads(line)["id"] for line in lines]
    assert ids == [1, 2, 3]


def test_every_line_has_trailing_newline(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    text = (tmp_path / MODEL_DIR / "element.jsonl").read_text()
    assert text.endswith("\n")
    assert len(text.splitlines()) == 3


def test_empty_table_is_zero_byte_file(tmp_path: Path) -> None:
    SnapshotCodec().write(_empty_snapshot(), tmp_path)
    assert (tmp_path / MODEL_DIR / "element.jsonl").read_bytes() == b""


# ---- value fidelity ----


def test_key_order_matches_column_names(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    line = (tmp_path / MODEL_DIR / "element.jsonl").read_text().splitlines()[0]
    keys = list(json.loads(line, object_pairs_hook=lambda pairs: dict(pairs)).keys())
    from pycadwork.persistence.schema import ELEMENT

    assert tuple(keys) == ELEMENT.column_names


def test_parent_container_id_serializes_as_null_and_int(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    rows = {
        obj["id"]: obj
        for obj in (
            json.loads(line)
            for line in (tmp_path / MODEL_DIR / "element.jsonl")
            .read_text()
            .splitlines()
        )
    }
    # key always present; None -> JSON null, int -> int
    assert '"parent_container_id":null' in json.dumps(rows[3], separators=(",", ":"))
    assert rows[1]["parent_container_id"] is None
    assert rows[2]["parent_container_id"] == 1


def test_spans_serializes_as_native_bool(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    text = (tmp_path / MODEL_DIR / "storey_assignment.jsonl").read_text()
    assert '"spans":true' in text
    assert '"spans":false' in text
    # native JSON booleans, never 1/0
    assert '"spans":1' not in text and '"spans":0' not in text


def test_awkward_floats_round_trip_exactly(tmp_path: Path) -> None:
    snap = ModelSnapshot(
        project=ProjectRecord(GUID),
        geometries=(
            GeometryRecord(GUID, 1, p1x=0.1, p1y=2999.9999999999995, volume=1e-9),
        ),
    )
    SnapshotCodec().write(snap, tmp_path)
    restored = SnapshotCodec().read(tmp_path)
    assert restored.geometries[0] == snap.geometries[0]


# ---- manifest ----


def test_manifest_records_document_file(tmp_path: Path) -> None:
    SnapshotCodec().write(_empty_snapshot(), tmp_path, document_file="Tower.3dc")
    manifest = SnapshotCodec().read_manifest(tmp_path)
    assert manifest.document_file == "Tower.3dc"
    assert manifest.format_version == FORMAT_VERSION
    assert manifest.project_guid == GUID


def test_missing_manifest_raises(tmp_path: Path) -> None:
    with pytest.raises(CodecError):
        SnapshotCodec().read_manifest(tmp_path)


def test_unknown_format_version_raises(tmp_path: Path) -> None:
    SnapshotCodec().write(_empty_snapshot(), tmp_path)
    path = tmp_path / MANIFEST_FILE
    payload = json.loads(path.read_text())
    payload["format_version"] = 999
    path.write_text(json.dumps(payload))
    with pytest.raises(CodecError):
        SnapshotCodec().read_manifest(tmp_path)


def test_malformed_manifest_raises(tmp_path: Path) -> None:
    (tmp_path / MANIFEST_FILE).write_text("{not json")
    with pytest.raises(CodecError):
        SnapshotCodec().read_manifest(tmp_path)


# ---- conflict / corruption ----


def test_conflict_marker_line_raises(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    element_file = tmp_path / MODEL_DIR / "element.jsonl"
    element_file.write_text(
        "<<<<<<< HEAD\n" + element_file.read_text() + ">>>>>>> branch\n"
    )
    with pytest.raises(CodecError):
        SnapshotCodec().read(tmp_path)


def test_bad_json_line_raises(tmp_path: Path) -> None:
    SnapshotCodec().write(_populated_snapshot(), tmp_path)
    (tmp_path / MODEL_DIR / "element.jsonl").write_text("{not valid json}\n")
    with pytest.raises(CodecError):
        SnapshotCodec().read(tmp_path)


# ---- map integrity (meta-test) ----


def test_table_specs_align_with_records_and_schema() -> None:
    from pycadwork.persistence.schema import TABLE_DEFS

    assert len(TABLE_SPECS) == len(TABLE_DEFS)
    for spec, table in zip(TABLE_SPECS, TABLE_DEFS):
        assert spec.table is table
        field_names = tuple(f.name for f in dataclasses.fields(spec.record_cls))
        assert (
            field_names == table.column_names
        ), f"{spec.record_cls.__name__} fields drifted from {table.name} columns"


def test_table_specs_cover_every_snapshot_tuple_field() -> None:
    tuple_fields = {
        f.name for f in dataclasses.fields(ModelSnapshot) if f.name != "project"
    }
    spec_fields = {spec.snapshot_field for spec in TABLE_SPECS if not spec.is_project}
    assert spec_fields == tuple_fields

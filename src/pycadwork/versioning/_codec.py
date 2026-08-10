"""SnapshotCodec — the pure JSONL serializer that makes a snapshot git-diffable.

A :class:`~pycadwork.persistence.records.ModelSnapshot` is the frozen, SQL-native
projection of the live model (:meth:`pycadwork.persistence.ModelReader.read`).
This codec materializes that snapshot as a *working tree* of per-table JSONL
files — one newline-delimited JSON object per record, sorted by primary key — so
that two snapshots produce byte-identical bytes when equal and minimal,
line-local diffs when they differ. Floats are quantized on write (see
:data:`FLOAT_SIGNIFICANT_DIGITS`) so that cross-environment ULP drift does not
register as a spurious diff. It reads the tree straight back into a
``ModelSnapshot`` equal to the (quantized) original.

The codec is **pure**: stdlib ``json`` / ``pathlib`` only, no cadwork, no git. It
lives in :mod:`pycadwork.versioning` (not ``persistence``) because making a
snapshot diffable is a versioning concern; it consumes ``persistence.records`` /
``persistence.schema`` read-only as the documented lingua franca — the same
one-way dependency :mod:`pycadwork.reporting` already follows.

The on-disk layout::

    <root>/
        manifest.json                  # format_version, project_guid, version, document_file
        model/
            project.jsonl  element.jsonl  attribute.jsonl  geometry.jsonl
            user_attribute.jsonl  cover.jsonl  container_member.jsonl
            building.jsonl  storey.jsonl  storey_assignment.jsonl
            material.jsonl  element_material.jsonl

Each table's JSON key order is its :attr:`~pycadwork.persistence.sql.Table.column_names`
(== record field order, by the schema's own guarantee), and its sort key is the
table's :attr:`~pycadwork.persistence.sql.Table.primary_key`. The typed-id fields
are :func:`typing.NewType` aliases — transparent ``int`` / ``str`` at runtime — so
``json`` serializes them directly and ``record_cls(**obj)`` accepts them with no
wrap/unwrap step.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

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
from pycadwork.persistence.schema import (
    ATTRIBUTE,
    BUILDING,
    CONTAINER_MEMBER,
    COVER,
    ELEMENT,
    ELEMENT_MATERIAL,
    GEOMETRY,
    MATERIAL,
    PROJECT,
    STOREY,
    STOREY_ASSIGNMENT,
    USER_ATTRIBUTE,
)
from pycadwork.persistence.sql import Table

#: The serialization format the manifest is stamped with. A reader refuses any
#: other value — a forward-incompatible tree fails loudly rather than silently
#: mis-parsing.
FORMAT_VERSION = 1

#: Floats are quantized to this many significant digits before serialization.
#: The same logical geometry computed on different CPUs / cadwork builds drifts
#: by 1–2 ULP in a double's least-significant bits, so an unchanged model would
#: otherwise emit ``2999.9999999999995`` on one machine and ``3000.0000000000002``
#: on another — a spurious, never-resolving line diff. Rounding to a fixed number
#: of *significant digits* (not decimal places: at building-scale magnitudes a
#: double cannot even hold a fixed decimal precision, so decimal rounding would
#: leave the drift untouched) collapses such values to byte-identical JSONL while
#: preserving sub-micron precision at building scale — twelve digits sits well
#: below a double's ~15–16 digit precision, so it absorbs ULP-level drift without
#: discarding anything physically meaningful.
FLOAT_SIGNIFICANT_DIGITS = 12

#: The subdirectory under the working tree that holds the per-table JSONL files.
MODEL_DIR = "model"

#: The manifest filename at the working-tree root.
MANIFEST_FILE = "manifest.json"

#: Git-conflict marker prefixes — their presence in a JSONL file means an
#: unresolved merge, which the codec refuses rather than mis-parsing.
_CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>")


class CodecError(RuntimeError):
    """A working tree could not be read as a valid snapshot.

    Raised on a malformed / unreadable manifest, an unsupported
    ``format_version``, or a JSONL line that is not a single JSON object
    (including an unresolved git-conflict marker).
    """


@dataclass(frozen=True, slots=True)
class Manifest:
    """The working tree's metadata sidecar (``manifest.json``).

    ``document_file`` records the basename of the binary ``.3dc`` committed
    alongside the JSONL, so a checkout/restore can find the right tracked file
    even after the project was renamed across branches. The codec only records
    the name; it never reads or writes the binary itself.
    """

    format_version: int
    project_guid: str
    pycadwork_version: str
    document_file: str = ""


@dataclass(frozen=True, slots=True)
class _TableSpec:
    """One table's serialization binding: its schema, record class, and snapshot field.

    ``snapshot_field`` is the attribute on :class:`ModelSnapshot` holding this
    table's records (a tuple for every table except ``project``, which is the
    single anchor record — see :attr:`is_project`).
    """

    table: Table
    record_cls: type
    snapshot_field: str

    @property
    def filename(self) -> str:
        """The JSONL filename for this table (``<table name>.jsonl``)."""
        return f"{self.table.name}.jsonl"

    @property
    def is_project(self) -> bool:
        """True for the single-row ``project`` anchor table."""
        return self.table is PROJECT


#: The parallel table↔record↔field bindings, in schema (foreign-key-safe) order.
#: A meta-test (``test_codec``) asserts every record's dataclass fields match its
#: table's column names, so a future schema change fails loudly here.
TABLE_SPECS: tuple[_TableSpec, ...] = (
    _TableSpec(PROJECT, ProjectRecord, "project"),
    _TableSpec(ELEMENT, ElementRecord, "elements"),
    _TableSpec(ATTRIBUTE, AttributeRecord, "attributes"),
    _TableSpec(GEOMETRY, GeometryRecord, "geometries"),
    _TableSpec(USER_ATTRIBUTE, UserAttributeRecord, "user_attributes"),
    _TableSpec(COVER, CoverRecord, "covers"),
    _TableSpec(CONTAINER_MEMBER, ContainerMemberRecord, "container_members"),
    _TableSpec(BUILDING, BuildingRecord, "buildings"),
    _TableSpec(STOREY, StoreyRecord, "storeys"),
    _TableSpec(STOREY_ASSIGNMENT, StoreyAssignmentRecord, "storey_assignments"),
    _TableSpec(MATERIAL, MaterialRecord, "materials"),
    _TableSpec(ELEMENT_MATERIAL, ElementMaterialRecord, "element_materials"),
)


def _pycadwork_version() -> str:
    """The installed package version for the manifest (``"unknown"`` if absent)."""
    try:
        return version("pycadwork")
    except PackageNotFoundError:  # pragma: no cover - only if run uninstalled
        return "unknown"


def _quantize(value: Any, significant_digits: int) -> Any:
    """Round a float to ``significant_digits`` to absorb cross-environment drift.

    Non-float values pass through untouched (``bool`` is an ``int`` subclass, so
    it is never mistaken for a float). Zero, infinities, and NaN are returned as
    is — except a negative zero is normalized to ``0.0``, since the sign of zero
    can flip across environments and would otherwise be its own spurious diff.
    See :data:`FLOAT_SIGNIFICANT_DIGITS` for why this is significant-digit, not
    decimal-place, rounding.
    """
    if type(value) is not float:
        return value
    if not math.isfinite(value):
        return value
    if value == 0.0:
        return 0.0  # collapse -0.0 → 0.0
    exponent = math.floor(math.log10(abs(value)))
    return round(value, significant_digits - 1 - exponent)


def _record_to_dict(
    record: object, columns: tuple[str, ...], significant_digits: int
) -> dict[str, Any]:
    """Build a dict in column order (so JSON keys follow field order), quantizing
    each float to ``significant_digits`` to keep equal models byte-identical."""
    return {
        name: _quantize(getattr(record, name), significant_digits) for name in columns
    }


def _sort_key(table: Table) -> Any:
    """A callable keying a record by its table's primary-key columns, in order."""
    pk = table.primary_key
    return lambda record: tuple(getattr(record, name) for name in pk)


def _dump_line(obj: dict[str, Any]) -> str:
    """One compact JSON object on one line (UTF-8 text, no ASCII escaping)."""
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


class SnapshotCodec:
    """Read/write a :class:`ModelSnapshot` as a deterministic JSONL working tree.

    Floats are quantized to ``float_significant_digits`` on write so that
    environment-induced drift in a double's least-significant bits does not show
    up as a spurious diff (see :data:`FLOAT_SIGNIFICANT_DIGITS`). Reads are
    faithful — they parse exactly what is on disk.
    """

    __slots__ = ("_float_sig",)

    def __init__(
        self, *, float_significant_digits: int = FLOAT_SIGNIFICANT_DIGITS
    ) -> None:
        if float_significant_digits < 1:
            raise ValueError("float_significant_digits must be >= 1")
        self._float_sig = float_significant_digits

    # ---- write ----

    def write(
        self, snapshot: ModelSnapshot, root: Path, *, document_file: str = ""
    ) -> list[Path]:
        """Materialize ``snapshot`` under ``root``; return every path written.

        Writes ``manifest.json`` plus one ``model/<table>.jsonl`` per table.
        Records are sorted by primary key so output is byte-identical for equal
        snapshots regardless of the reader's emission order; an empty table
        yields a zero-byte file so a table emptying out shows as a real diff.
        Every line ends in ``\\n`` so a one-line change is a one-line diff.
        """
        root = Path(root)
        model_dir = root / MODEL_DIR
        model_dir.mkdir(parents=True, exist_ok=True)

        manifest = Manifest(
            format_version=FORMAT_VERSION,
            project_guid=str(snapshot.project.project_guid),
            pycadwork_version=_pycadwork_version(),
            document_file=document_file,
        )
        written: list[Path] = [self._write_manifest(root, manifest)]

        for spec in TABLE_SPECS:
            records = self._records_for(snapshot, spec)
            written.append(self._write_table(model_dir, spec, records))
        return written

    def _write_manifest(self, root: Path, manifest: Manifest) -> Path:
        path = root / MANIFEST_FILE
        payload = {
            "format_version": manifest.format_version,
            "project_guid": manifest.project_guid,
            "pycadwork_version": manifest.pycadwork_version,
            "document_file": manifest.document_file,
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return path

    def _records_for(self, snapshot: ModelSnapshot, spec: _TableSpec) -> list[object]:
        if spec.is_project:
            return [snapshot.project]
        return list(getattr(snapshot, spec.snapshot_field))

    def _write_table(
        self, model_dir: Path, spec: _TableSpec, records: list[object]
    ) -> Path:
        path = model_dir / spec.filename
        columns = spec.table.column_names
        ordered = sorted(records, key=_sort_key(spec.table))
        lines = [
            _dump_line(_record_to_dict(r, columns, self._float_sig)) for r in ordered
        ]
        text = "".join(line + "\n" for line in lines)
        path.write_text(text, encoding="utf-8")
        return path

    # ---- read ----

    def read_manifest(self, root: Path) -> Manifest:
        """Parse and validate ``root/manifest.json`` into a :class:`Manifest`.

        Raises :class:`CodecError` on a missing / unparseable manifest or an
        unsupported ``format_version``.
        """
        path = Path(root) / MANIFEST_FILE
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise CodecError(f"no manifest at {path}") from exc
        return self._parse_manifest_text(text, str(path))

    def _parse_manifest_text(self, text: str, source: str) -> Manifest:
        """Parse manifest JSON already read from disk or a git ref."""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CodecError(f"malformed manifest at {source}: {exc}") from exc
        if not isinstance(payload, dict):
            raise CodecError(f"manifest at {source} is not a JSON object")

        format_version = payload.get("format_version")
        if format_version != FORMAT_VERSION:
            raise CodecError(
                f"unsupported format_version {format_version!r} at {source} "
                f"(this build reads {FORMAT_VERSION})"
            )
        return Manifest(
            format_version=format_version,
            project_guid=str(payload.get("project_guid", "")),
            pycadwork_version=str(payload.get("pycadwork_version", "")),
            document_file=str(payload.get("document_file", "")),
        )

    def read(self, root: Path) -> ModelSnapshot:
        """Reassemble the :class:`ModelSnapshot` stored under ``root``.

        Mirrors :func:`pycadwork.persistence.load_snapshot`: a missing or empty
        ``project.jsonl`` yields a default ``ProjectRecord`` keyed by the
        manifest's ``project_guid`` so the snapshot always has an anchor.
        """
        root = Path(root)
        manifest = self.read_manifest(root)
        model_dir = root / MODEL_DIR

        fields_by_name: dict[str, Any] = {}
        for spec in TABLE_SPECS:
            records = self._read_table(model_dir, spec)
            if spec.is_project:
                fields_by_name["project"] = (
                    records[0]
                    if records
                    else ProjectRecord(manifest.project_guid)  # type: ignore[arg-type]
                )
            else:
                fields_by_name[spec.snapshot_field] = tuple(records)
        return ModelSnapshot(**fields_by_name)

    def _read_table(self, model_dir: Path, spec: _TableSpec) -> list[object]:
        path = model_dir / spec.filename
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return []
        return self._parse_table_text(text, spec, str(path))

    def _parse_table_text(
        self, text: str, spec: _TableSpec, source: str
    ) -> list[object]:
        """Parse one table's JSONL text already read from disk or a git ref."""
        records: list[object] = []
        for number, raw in enumerate(text.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            if line.startswith(_CONFLICT_MARKERS):
                raise CodecError(
                    f"unresolved merge conflict in {source} (line {number})"
                )
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CodecError(
                    f"bad JSON in {source} (line {number}): {exc}"
                ) from exc
            if not isinstance(obj, dict):
                raise CodecError(f"non-object JSON in {source} (line {number})")
            try:
                records.append(spec.record_cls(**obj))
            except TypeError as exc:
                raise CodecError(
                    f"record mismatch in {source} (line {number}): {exc}"
                ) from exc
        return records

    def table_filenames(self) -> tuple[str, ...]:
        """Every ``model/<table>.jsonl`` filename, in schema order.

        Lets a caller fetch each table's raw text from an arbitrary source
        (e.g. :meth:`~pycadwork.versioning.Repository.read_file_at_ref`) without
        reaching into :data:`TABLE_SPECS` directly.
        """
        return tuple(spec.filename for spec in TABLE_SPECS)

    def read_texts(
        self, manifest_text: str, table_texts: dict[str, str]
    ) -> ModelSnapshot:
        """Assemble a :class:`ModelSnapshot` from raw text instead of disk.

        ``table_texts`` maps a filename from :meth:`table_filenames` to its
        JSONL text (an absent or empty entry is treated as an empty table).
        This is what a pre-checkout preview needs: the caller fetches each
        file's content at a ref (e.g. via ``git show <ref>:<path>``) without
        ever checking it out, then reassembles the snapshot exactly like
        :meth:`read` would from disk.
        """
        manifest = self._parse_manifest_text(manifest_text, "<manifest>")

        fields_by_name: dict[str, Any] = {}
        for spec in TABLE_SPECS:
            text = table_texts.get(spec.filename, "")
            records = (
                self._parse_table_text(text, spec, f"<{spec.filename}>")
                if text.strip()
                else []
            )
            if spec.is_project:
                fields_by_name["project"] = (
                    records[0]
                    if records
                    else ProjectRecord(manifest.project_guid)  # type: ignore[arg-type]
                )
            else:
                fields_by_name[spec.snapshot_field] = tuple(records)
        return ModelSnapshot(**fields_by_name)

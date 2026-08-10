"""The normalized SQL schema, declared as data and rendered to DDL.

Each table is one :class:`~pycadwork.persistence.sql.Table` literal — the
*single source of truth* for that table's shape. :data:`SCHEMA_SQL` is then
*generated* from those literals via :func:`~pycadwork.persistence.sql.create_table`
(no hand-written DDL), and the gateways in
:mod:`pycadwork.persistence.gateways` read their column / key sets off the very
same ``Table`` objects, so a table is described in exactly one place.

``SCHEMA_SQL`` is a single ``CREATE TABLE IF NOT EXISTS`` script — embedding it
in Python (rather than shipping a ``.sql`` file) means hatch packages it into the
wheel automatically. Running it is idempotent, so
:func:`pycadwork.persistence.open_sqlite` can apply it on every open.

The 10 tables form a 3NF model: ``project`` and ``element`` are the parents;
``attribute`` and ``geometry`` are 1:1 satellites split off ``element`` to keep
it lean across heterogeneous types; ``user_attribute`` and ``container_member``
are proper 1:M tables (no array columns); ``building`` / ``storey`` /
``storey_assignment`` carry the BMT structure. Every column order here matches
the field order of the matching record in :mod:`pycadwork.persistence.records`,
so the gateways can (de)serialize positionally.

Cover *membership* is deliberately absent: it is the projection "elements whose
group/subgroup key equals a cover parent's key" and is reconstructed on read via
that join (see ``CoverBuilder._by_grouping``). Storing it would be a derived
redundancy. Foreign keys cascade on delete so a ``pull`` that drops a missing
element row also drops its satellites in one statement (requires
``PRAGMA foreign_keys = ON``, which :class:`SqliteConnection` sets on open).
"""

from __future__ import annotations

from pycadwork.persistence.sql import (
    Column,
    ColumnType,
    ForeignKey,
    Table,
    create_table,
)

_TEXT = ColumnType.TEXT
_INTEGER = ColumnType.INTEGER
_REAL = ColumnType.REAL


def _text(name: str) -> Column:
    """A required text column defaulting to the empty string."""
    return Column(name, _TEXT, default="")


def _real(name: str) -> Column:
    """A required real column defaulting to ``0.0``."""
    return Column(name, _REAL, default=0.0)


PROJECT = Table(
    name="project",
    columns=(
        Column("project_guid", _TEXT),
        _text("name"),
        _text("number"),
        _text("part"),
        _text("architect"),
        _text("customer"),
        _text("designer"),
        _text("deadline"),
        _text("description"),
        _text("address"),
        _text("postal_code"),
        _text("city"),
        _text("country"),
        _real("latitude"),
        _real("longitude"),
        _real("elevation"),
    ),
    primary_key=("project_guid",),
)

ELEMENT = Table(
    name="element",
    columns=(
        Column("project_guid", _TEXT),
        Column("id", _INTEGER),
        Column("element_type", _TEXT),
        _text("cadwork_guid"),
        Column("parent_container_id", _INTEGER, not_null=False),
    ),
    primary_key=("project_guid", "id"),
    foreign_keys=(ForeignKey(("project_guid",), "project", ("project_guid",)),),
)

ATTRIBUTE = Table(
    name="attribute",
    columns=(
        Column("project_guid", _TEXT),
        Column("element_id", _INTEGER),
        _text("name"),
        _text("group_name"),
        _text("subgroup"),
        _text("comment"),
        _text("material_name"),
        _text("sku"),
        Column("production_number", _INTEGER, default=0),
        _text("part_number"),
        _text("assembly_number"),
    ),
    primary_key=("project_guid", "element_id"),
    foreign_keys=(
        ForeignKey(("project_guid", "element_id"), "element", ("project_guid", "id")),
    ),
)

GEOMETRY = Table(
    name="geometry",
    columns=(
        Column("project_guid", _TEXT),
        Column("element_id", _INTEGER),
        _real("p1x"),
        _real("p1y"),
        _real("p1z"),
        _real("p2x"),
        _real("p2y"),
        _real("p2z"),
        _real("p3x"),
        _real("p3y"),
        _real("p3z"),
        _real("length"),
        _real("width"),
        _real("height"),
        _real("volume"),
        _real("weight"),
        _real("cog_x"),
        _real("cog_y"),
        _real("cog_z"),
        _real("aabb_min_x"),
        _real("aabb_min_y"),
        _real("aabb_min_z"),
        _real("aabb_max_x"),
        _real("aabb_max_y"),
        _real("aabb_max_z"),
    ),
    primary_key=("project_guid", "element_id"),
    foreign_keys=(
        ForeignKey(("project_guid", "element_id"), "element", ("project_guid", "id")),
    ),
)

USER_ATTRIBUTE = Table(
    name="user_attribute",
    columns=(
        Column("project_guid", _TEXT),
        Column("element_id", _INTEGER),
        Column("attr_index", _INTEGER),
        _text("value"),
    ),
    primary_key=("project_guid", "element_id", "attr_index"),
    foreign_keys=(
        ForeignKey(("project_guid", "element_id"), "element", ("project_guid", "id")),
    ),
)

COVER = Table(
    name="cover",
    columns=(
        Column("project_guid", _TEXT),
        Column("element_id", _INTEGER),
        Column("cover_kind", _TEXT),
    ),
    primary_key=("project_guid", "element_id"),
    foreign_keys=(
        ForeignKey(("project_guid", "element_id"), "element", ("project_guid", "id")),
    ),
)

CONTAINER_MEMBER = Table(
    name="container_member",
    columns=(
        Column("project_guid", _TEXT),
        Column("container_id", _INTEGER),
        Column("member_id", _INTEGER),
    ),
    primary_key=("project_guid", "container_id", "member_id"),
    foreign_keys=(
        ForeignKey(("project_guid", "container_id"), "element", ("project_guid", "id")),
        ForeignKey(("project_guid", "member_id"), "element", ("project_guid", "id")),
    ),
)

BUILDING = Table(
    name="building",
    columns=(
        Column("project_guid", _TEXT),
        Column("name", _TEXT),
    ),
    primary_key=("project_guid", "name"),
    foreign_keys=(ForeignKey(("project_guid",), "project", ("project_guid",)),),
)

STOREY = Table(
    name="storey",
    columns=(
        Column("project_guid", _TEXT),
        Column("building_name", _TEXT),
        Column("name", _TEXT),
        _real("elevation"),
    ),
    primary_key=("project_guid", "building_name", "name"),
    foreign_keys=(
        ForeignKey(
            ("project_guid", "building_name"), "building", ("project_guid", "name")
        ),
    ),
)

STOREY_ASSIGNMENT = Table(
    name="storey_assignment",
    columns=(
        Column("project_guid", _TEXT),
        Column("element_id", _INTEGER),
        Column("building_name", _TEXT),
        Column("storey_name", _TEXT),
        Column("spans", _INTEGER, default=0),
    ),
    primary_key=("project_guid", "element_id"),
    foreign_keys=(
        ForeignKey(("project_guid", "element_id"), "element", ("project_guid", "id")),
        ForeignKey(
            ("project_guid", "building_name", "storey_name"),
            "storey",
            ("project_guid", "building_name", "name"),
        ),
    ),
)

MATERIAL = Table(
    name="material",
    columns=(
        Column("project_guid", _TEXT),
        Column("material_name", _TEXT),
        _text("group_name"),
        _text("code"),
        _text("grade"),
        _text("quality"),
        _real("modulus_elasticity_1"),
        _real("modulus_elasticity_2"),
        _real("modulus_elasticity_3"),
        _real("shear_modulus_1"),
        _real("shear_modulus_2"),
        _real("weight"),
    ),
    primary_key=("project_guid", "material_name"),
    foreign_keys=(ForeignKey(("project_guid",), "project", ("project_guid",)),),
)

ELEMENT_MATERIAL = Table(
    name="element_material",
    columns=(
        Column("project_guid", _TEXT),
        Column("element_id", _INTEGER),
        _text("cadwork_guid"),
        _text("material_name"),
    ),
    primary_key=("project_guid", "element_id"),
    foreign_keys=(
        ForeignKey(("project_guid", "element_id"), "element", ("project_guid", "id")),
        ForeignKey(
            ("project_guid", "material_name"),
            "material",
            ("project_guid", "material_name"),
        ),
    ),
)

# The twelve tables, in foreign-key-safe creation order: parents before children.
# ``material`` (FK → project) and ``element_material`` (FK → element + material)
# come last, after every table they reference.
TABLE_DEFS: tuple[Table, ...] = (
    PROJECT,
    ELEMENT,
    ATTRIBUTE,
    GEOMETRY,
    USER_ATTRIBUTE,
    COVER,
    CONTAINER_MEMBER,
    BUILDING,
    STOREY,
    STOREY_ASSIGNMENT,
    MATERIAL,
    ELEMENT_MATERIAL,
)

# Their names, same order — the public list the connection/tests rely on.
TABLES: tuple[str, ...] = tuple(table.name for table in TABLE_DEFS)

# The full idempotent DDL script, generated from the table definitions.
SCHEMA_SQL: str = "\n\n".join(create_table(table) for table in TABLE_DEFS)

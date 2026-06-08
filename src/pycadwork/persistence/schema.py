"""The normalized SQL schema, embedded as one DDL string.

``SCHEMA_SQL`` is a single ``CREATE TABLE IF NOT EXISTS`` script — embedding it
in Python (rather than shipping a ``.sql`` file) means hatch packages it into
the wheel automatically, with no package-data configuration. Running it is
idempotent, so :func:`pycadwork.persistence.open_sqlite` can apply it on every
open.

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

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS project (
    project_guid TEXT PRIMARY KEY,
    name         TEXT NOT NULL DEFAULT '',
    number       TEXT NOT NULL DEFAULT '',
    part         TEXT NOT NULL DEFAULT '',
    architect    TEXT NOT NULL DEFAULT '',
    customer     TEXT NOT NULL DEFAULT '',
    designer     TEXT NOT NULL DEFAULT '',
    deadline     TEXT NOT NULL DEFAULT '',
    description  TEXT NOT NULL DEFAULT '',
    address      TEXT NOT NULL DEFAULT '',
    postal_code  TEXT NOT NULL DEFAULT '',
    city         TEXT NOT NULL DEFAULT '',
    country      TEXT NOT NULL DEFAULT '',
    latitude     REAL NOT NULL DEFAULT 0.0,
    longitude    REAL NOT NULL DEFAULT 0.0,
    elevation    REAL NOT NULL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS element (
    project_guid        TEXT NOT NULL,
    id                  INTEGER NOT NULL,
    element_type        TEXT NOT NULL,
    cadwork_guid        TEXT NOT NULL DEFAULT '',
    parent_container_id INTEGER,
    PRIMARY KEY (project_guid, id),
    FOREIGN KEY (project_guid) REFERENCES project (project_guid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attribute (
    project_guid      TEXT NOT NULL,
    element_id        INTEGER NOT NULL,
    name              TEXT NOT NULL DEFAULT '',
    group_name        TEXT NOT NULL DEFAULT '',
    subgroup          TEXT NOT NULL DEFAULT '',
    comment           TEXT NOT NULL DEFAULT '',
    material_name     TEXT NOT NULL DEFAULT '',
    sku               TEXT NOT NULL DEFAULT '',
    production_number INTEGER NOT NULL DEFAULT 0,
    part_number       TEXT NOT NULL DEFAULT '',
    assembly_number   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (project_guid, element_id),
    FOREIGN KEY (project_guid, element_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS geometry (
    project_guid TEXT NOT NULL,
    element_id   INTEGER NOT NULL,
    p1x REAL NOT NULL DEFAULT 0.0,
    p1y REAL NOT NULL DEFAULT 0.0,
    p1z REAL NOT NULL DEFAULT 0.0,
    p2x REAL NOT NULL DEFAULT 0.0,
    p2y REAL NOT NULL DEFAULT 0.0,
    p2z REAL NOT NULL DEFAULT 0.0,
    p3x REAL NOT NULL DEFAULT 0.0,
    p3y REAL NOT NULL DEFAULT 0.0,
    p3z REAL NOT NULL DEFAULT 0.0,
    length REAL NOT NULL DEFAULT 0.0,
    width  REAL NOT NULL DEFAULT 0.0,
    height REAL NOT NULL DEFAULT 0.0,
    volume REAL NOT NULL DEFAULT 0.0,
    weight REAL NOT NULL DEFAULT 0.0,
    cog_x REAL NOT NULL DEFAULT 0.0,
    cog_y REAL NOT NULL DEFAULT 0.0,
    cog_z REAL NOT NULL DEFAULT 0.0,
    aabb_min_x REAL NOT NULL DEFAULT 0.0,
    aabb_min_y REAL NOT NULL DEFAULT 0.0,
    aabb_min_z REAL NOT NULL DEFAULT 0.0,
    aabb_max_x REAL NOT NULL DEFAULT 0.0,
    aabb_max_y REAL NOT NULL DEFAULT 0.0,
    aabb_max_z REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (project_guid, element_id),
    FOREIGN KEY (project_guid, element_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_attribute (
    project_guid TEXT NOT NULL,
    element_id   INTEGER NOT NULL,
    attr_index   INTEGER NOT NULL,
    value        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (project_guid, element_id, attr_index),
    FOREIGN KEY (project_guid, element_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cover (
    project_guid TEXT NOT NULL,
    element_id   INTEGER NOT NULL,
    cover_kind   TEXT NOT NULL,
    PRIMARY KEY (project_guid, element_id),
    FOREIGN KEY (project_guid, element_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS container_member (
    project_guid TEXT NOT NULL,
    container_id INTEGER NOT NULL,
    member_id    INTEGER NOT NULL,
    PRIMARY KEY (project_guid, container_id, member_id),
    FOREIGN KEY (project_guid, container_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE,
    FOREIGN KEY (project_guid, member_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS building (
    project_guid TEXT NOT NULL,
    name         TEXT NOT NULL,
    PRIMARY KEY (project_guid, name),
    FOREIGN KEY (project_guid) REFERENCES project (project_guid) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS storey (
    project_guid  TEXT NOT NULL,
    building_name TEXT NOT NULL,
    name          TEXT NOT NULL,
    elevation     REAL NOT NULL DEFAULT 0.0,
    PRIMARY KEY (project_guid, building_name, name),
    FOREIGN KEY (project_guid, building_name)
        REFERENCES building (project_guid, name) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS storey_assignment (
    project_guid  TEXT NOT NULL,
    element_id    INTEGER NOT NULL,
    building_name TEXT NOT NULL,
    storey_name   TEXT NOT NULL,
    spans         INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (project_guid, element_id),
    FOREIGN KEY (project_guid, element_id)
        REFERENCES element (project_guid, id) ON DELETE CASCADE,
    FOREIGN KEY (project_guid, building_name, storey_name)
        REFERENCES storey (project_guid, building_name, name) ON DELETE CASCADE
);
"""

# The ten tables the schema defines, in foreign-key-safe creation order.
TABLES: tuple[str, ...] = (
    "project",
    "element",
    "attribute",
    "geometry",
    "user_attribute",
    "cover",
    "container_member",
    "building",
    "storey",
    "storey_assignment",
)

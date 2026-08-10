"""pycadwork.reporting — bill of materials / quantity takeoff over a snapshot.

Pure report functions over a
:class:`~pycadwork.persistence.records.ModelSnapshot`: a cutting list (one row
per part identity, identical parts collapsed to a count) and material totals,
each groupable by composable :class:`Dimension` axes — per material, group,
subgroup, storey, or owning cover. Nothing here imports cadwork or touches
SQL, so the whole module is unit-testable from record literals.

Both snapshot sources feed the same functions::

    from pycadwork.persistence import ModelReader, Synchronizer, load_snapshot, open_sqlite
    from pycadwork.reporting import by_material, by_storey, cutting_list

    # live model
    rows = cutting_list(ModelReader().read(), dimensions=(by_material(),))

    # pulled SQL store — identical rows
    connection = open_sqlite("model.db")
    Synchronizer().pull(connection)
    rows = cutting_list(
        load_snapshot(connection, guid), dimensions=(by_storey(), by_material())
    )
"""

from __future__ import annotations

from pycadwork.reporting.csv_export import write_material_totals_csv, write_parts_csv
from pycadwork.reporting.dimensions import (
    Dimension,
    by_cover,
    by_group,
    by_material,
    by_storey,
    by_subgroup,
)
from pycadwork.reporting.index import SnapshotIndex
from pycadwork.reporting.records import MaterialTotalRow, PartRow
from pycadwork.reporting.reports import (
    DEFAULT_PART_TYPES,
    cutting_list,
    material_totals,
)

__all__ = [
    "DEFAULT_PART_TYPES",
    "Dimension",
    "MaterialTotalRow",
    "PartRow",
    "SnapshotIndex",
    "by_cover",
    "by_group",
    "by_material",
    "by_storey",
    "by_subgroup",
    "cutting_list",
    "material_totals",
    "write_material_totals_csv",
    "write_parts_csv",
]

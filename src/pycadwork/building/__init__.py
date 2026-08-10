"""Building / storey spatial assignment.

Reads cadwork's BMT building→storey structure and assigns elements to storeys
automatically from geometry. The classification core (:class:`StoreyStack`) is
pure; :class:`StoreyAssigner` is the cadwork-touching orchestration.
"""

from __future__ import annotations

from pycadwork.building.assigner import StoreyAssigner, StoreyAssignment
from pycadwork.building.names import BuildingName, StoreyName
from pycadwork.building.storey import Storey, StoreyClassification, StoreyStack

__all__ = [
    "BuildingName",
    "Storey",
    "StoreyAssigner",
    "StoreyAssignment",
    "StoreyClassification",
    "StoreyName",
    "StoreyStack",
]

"""BuildingQuery — the read-side navigation facade over the SQL store.

Where :func:`pycadwork.persistence.load_snapshot` reassembles *every* table for a
project (the value the diff/sync needs), :class:`BuildingQuery` answers the three
BMT-structure questions directly: which buildings exist, which storeys sit under a
building, and which elements were assigned to a given storey. Each call is a scoped
gateway query — no whole-project load.

The facade holds no SQL of its own; it composes the gateways (honouring the package
rule that all SQL lives in :mod:`~pycadwork.persistence.gateways`). Gateways are cheap,
``__slots__``-only wrappers, so they are constructed per call as
:func:`~pycadwork.persistence.sync.load_snapshot` does.
"""

from __future__ import annotations

from pycadwork.persistence._connection import GatewayConnection
from pycadwork.persistence._ids import ProjectGuid
from pycadwork.persistence.gateways import (
    BuildingGateway,
    ElementGateway,
    StoreyAssignmentGateway,
    StoreyGateway,
)
from pycadwork.persistence.records import (
    BuildingRecord,
    ElementRecord,
    StoreyRecord,
)


class BuildingQuery:
    """Read-side navigation: building → storeys → elements, scoped to one project."""

    __slots__ = ("_connection", "_project_guid")

    def __init__(
        self, connection: GatewayConnection, project_guid: ProjectGuid
    ) -> None:
        self._connection = connection
        self._project_guid = project_guid

    def buildings(self) -> list[BuildingRecord]:
        """Every building in the project."""
        return BuildingGateway(self._connection).select_for_project(self._project_guid)

    def storeys(self, building_name: str) -> list[StoreyRecord]:
        """The storeys under ``building_name``, ascending by elevation.

        Ordering matches :class:`~pycadwork.building.storey.StoreyStack`, so the first
        element is the lowest storey. An unknown building yields ``[]``.
        """
        storeys = StoreyGateway(self._connection).select_for_building(
            self._project_guid, building_name
        )
        return sorted(storeys, key=lambda s: s.elevation)

    def elements(self, building_name: str, storey_name: str) -> list[ElementRecord]:
        """The elements assigned to one storey of one building, ascending by id.

        An unknown building/storey (or a storey with no assignments) yields ``[]``.
        """
        assignments = StoreyAssignmentGateway(self._connection).select_for_storey(
            self._project_guid, building_name, storey_name
        )
        ids = [a.element_id for a in assignments]
        elements = ElementGateway(self._connection).select_for_ids(
            self._project_guid, ids
        )
        return sorted(elements, key=lambda e: e.id)

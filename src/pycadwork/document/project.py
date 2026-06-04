"""The project-metadata surface for the active cadwork project.

``ProjectInfo`` is to the :class:`~pycadwork.document.document.Document` what
:class:`~pycadwork.element.components.attributes.Attributes` is to an
:class:`~pycadwork.element.base.Element`: a small live view where reads are
properties and writes are ``set_*`` methods. The project is global, so it
carries no id. All reads are live queries against the active backend.

Adding a new project field is the same three-step recipe as for element
attributes:
  1. Add the get/set pair on ``ProjectAdapter`` in ``cadwork_adapter/_project.py``.
  2. Mirror it on ``FakeProjectAdapter`` in ``tests/_fakes/cadwork_adapter.py``.
  3. Add the property / setter here.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter import cadwork


class ProjectInfo:
    """Read/write view of the active project's metadata and data store."""

    __slots__ = ()

    # ---- identity ----

    @property
    def guid(self) -> str:
        """The project GUID. Read-only in cwapi3d."""
        return cadwork.project.get_project_guid()

    def new_guid(self) -> str:
        """Generate a fresh GUID (cwapi3d's ``create_new_guid``)."""
        return cadwork.project.create_new_guid()

    # ---- metadata (str) ----

    @property
    def name(self) -> str:
        return cadwork.project.get_project_name()

    def set_name(self, value: str) -> None:
        cadwork.project.set_project_name(value)

    @property
    def number(self) -> str:
        return cadwork.project.get_project_number()

    def set_number(self, value: str) -> None:
        cadwork.project.set_project_number(value)

    @property
    def part(self) -> str:
        return cadwork.project.get_project_part()

    def set_part(self, value: str) -> None:
        cadwork.project.set_project_part(value)

    @property
    def architect(self) -> str:
        return cadwork.project.get_project_architect()

    def set_architect(self, value: str) -> None:
        cadwork.project.set_project_architect(value)

    @property
    def customer(self) -> str:
        return cadwork.project.get_project_customer()

    def set_customer(self, value: str) -> None:
        cadwork.project.set_project_customer(value)

    @property
    def designer(self) -> str:
        return cadwork.project.get_project_designer()

    def set_designer(self, value: str) -> None:
        cadwork.project.set_project_designer(value)

    @property
    def deadline(self) -> str:
        return cadwork.project.get_project_deadline()

    def set_deadline(self, value: str) -> None:
        cadwork.project.set_project_deadline(value)

    @property
    def description(self) -> str:
        return cadwork.project.get_project_description()

    def set_description(self, value: str) -> None:
        cadwork.project.set_project_description(value)

    # ---- address ----

    @property
    def address(self) -> str:
        return cadwork.project.get_project_address()

    def set_address(self, value: str) -> None:
        cadwork.project.set_project_address(value)

    @property
    def postal_code(self) -> str:
        return cadwork.project.get_project_postal_code()

    def set_postal_code(self, value: str) -> None:
        cadwork.project.set_project_postal_code(value)

    @property
    def city(self) -> str:
        return cadwork.project.get_project_city()

    def set_city(self, value: str) -> None:
        cadwork.project.set_project_city(value)

    @property
    def country(self) -> str:
        return cadwork.project.get_project_country()

    def set_country(self, value: str) -> None:
        cadwork.project.set_project_country(value)

    # ---- geo-location (float) ----

    @property
    def latitude(self) -> float:
        return cadwork.project.get_project_latitude()

    def set_latitude(self, value: float) -> None:
        cadwork.project.set_project_latitude(value)

    @property
    def longitude(self) -> float:
        return cadwork.project.get_project_longitude()

    def set_longitude(self, value: float) -> None:
        cadwork.project.set_project_longitude(value)

    @property
    def elevation(self) -> float:
        return cadwork.project.get_project_elevation()

    def set_elevation(self, value: float) -> None:
        cadwork.project.set_project_elevation(value)

    # ---- indexed user attributes ----

    def user_attribute(self, number: int) -> str:
        """Read project user attribute ``number``."""
        return cadwork.project.get_project_user_attribute(number)

    def set_user_attribute(self, number: int, value: str) -> None:
        cadwork.project.set_project_user_attribute(number, value)

    def user_attribute_name(self, number: int) -> str:
        return cadwork.project.get_project_user_attribute_name(number)

    def set_user_attribute_name(self, number: int, value: str) -> None:
        cadwork.project.set_project_user_attribute_name(number, value)

    # ---- project-data key/value store ----

    def data(self, key: str) -> str:
        """Read the project-data value stored under ``key``."""
        return cadwork.project.get_project_data(key)

    def set_data(self, key: str, value: str) -> None:
        cadwork.project.set_project_data(key, value)

    def delete_data(self, key: str) -> None:
        cadwork.project.delete_project_data(key)

    def data_keys(self) -> list[str]:
        """All keys currently present in the project-data store."""
        return cadwork.project.get_project_data_keys()

    def __repr__(self) -> str:
        return f"ProjectInfo(name={self.name!r}, guid={self.guid!r})"

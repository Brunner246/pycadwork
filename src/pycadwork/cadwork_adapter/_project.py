"""ProjectAdapter: project-level metadata, the project-data store, and GUIDs.

Wraps cadwork's ``utility_controller`` project surface. Unlike the other
sub-adapters this one is element-agnostic — the calls act on the active
project as a whole, so there are no element ids. Method names stay close to
cwapi3d (``..._project_...``); the friendly short names live on
:class:`pycadwork.document.project.ProjectInfo`.
"""
from __future__ import annotations


class ProjectAdapter:
    """Read/write the active project's metadata, data store, and GUIDs."""

    # ---- identity ----

    def get_project_guid(self) -> str:
        import utility_controller
        return utility_controller.get_project_guid()

    def create_new_guid(self) -> str:
        import utility_controller
        return utility_controller.create_new_guid()

    # ---- metadata (str) ----

    def get_project_name(self) -> str:
        import utility_controller
        return utility_controller.get_project_name()

    def set_project_name(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_name(value)

    def get_project_number(self) -> str:
        import utility_controller
        return utility_controller.get_project_number()

    def set_project_number(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_number(value)

    def get_project_part(self) -> str:
        import utility_controller
        return utility_controller.get_project_part()

    def set_project_part(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_part(value)

    def get_project_architect(self) -> str:
        import utility_controller
        return utility_controller.get_project_architect()

    def set_project_architect(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_architect(value)

    def get_project_customer(self) -> str:
        import utility_controller
        return utility_controller.get_project_customer()

    def set_project_customer(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_customer(value)

    def get_project_designer(self) -> str:
        import utility_controller
        return utility_controller.get_project_designer()

    def set_project_designer(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_designer(value)

    def get_project_deadline(self) -> str:
        import utility_controller
        return utility_controller.get_project_deadline()

    def set_project_deadline(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_deadline(value)

    def get_project_description(self) -> str:
        import utility_controller
        return utility_controller.get_project_description()

    def set_project_description(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_description(value)

    # ---- address ----

    def get_project_address(self) -> str:
        import utility_controller
        return utility_controller.get_project_address()

    def set_project_address(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_address(value)

    def get_project_postal_code(self) -> str:
        import utility_controller
        return utility_controller.get_project_postal_code()

    def set_project_postal_code(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_postal_code(value)

    def get_project_city(self) -> str:
        import utility_controller
        return utility_controller.get_project_city()

    def set_project_city(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_city(value)

    def get_project_country(self) -> str:
        import utility_controller
        return utility_controller.get_project_country()

    def set_project_country(self, value: str) -> None:
        import utility_controller
        utility_controller.set_project_country(value)

    # ---- geo-location (float) ----

    def get_project_latitude(self) -> float:
        import utility_controller
        return utility_controller.get_project_latitude()

    def set_project_latitude(self, value: float) -> None:
        import utility_controller
        utility_controller.set_project_latitude(value)

    def get_project_longitude(self) -> float:
        import utility_controller
        return utility_controller.get_project_longitude()

    def set_project_longitude(self, value: float) -> None:
        import utility_controller
        utility_controller.set_project_longitude(value)

    def get_project_elevation(self) -> float:
        import utility_controller
        return utility_controller.get_project_elevation()

    def set_project_elevation(self, value: float) -> None:
        import utility_controller
        utility_controller.set_project_elevation(value)

    # ---- indexed user attributes ----

    def get_project_user_attribute(self, number: int) -> str:
        import utility_controller
        return utility_controller.get_project_user_attribute(number)

    def set_project_user_attribute(self, number: int, value: str) -> None:
        import utility_controller
        utility_controller.set_project_user_attribute(number, value)

    def get_project_user_attribute_name(self, number: int) -> str:
        import utility_controller
        return utility_controller.get_project_user_attribute_name(number)

    def set_project_user_attribute_name(self, number: int, value: str) -> None:
        import utility_controller
        utility_controller.set_project_user_attribute_name(number, value)

    # ---- project-data key/value store ----

    def get_project_data(self, key: str) -> str:
        import utility_controller
        return utility_controller.get_project_data(key)

    def set_project_data(self, key: str, data: str) -> None:
        import utility_controller
        utility_controller.set_project_data(key, data)

    def delete_project_data(self, key: str) -> None:
        import utility_controller
        utility_controller.delete_project_data(key)

    def get_project_data_keys(self) -> list[str]:
        import utility_controller
        return utility_controller.get_project_data_keys()

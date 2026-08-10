"""Document.project: the project-metadata surface, round-tripped via the fake."""

from __future__ import annotations

import pytest

from pycadwork import Document, ProjectInfo


def test_project_is_a_projectinfo() -> None:
    assert isinstance(Document().project, ProjectInfo)


def test_guid_reads_from_the_backend() -> None:
    doc = Document()
    assert doc.project.guid == "fake-project-guid"
    # convenience delegate on the document
    assert doc.guid == doc.project.guid


def test_new_guid_returns_distinct_non_empty_strings() -> None:
    project = Document().project
    a, b = project.new_guid(), project.new_guid()
    assert a and b
    assert a != b


@pytest.mark.parametrize(
    ("setter", "getter", "value"),
    [
        ("set_name", "name", "House A"),
        ("set_number", "number", "2026-017"),
        ("set_part", "part", "Roof"),
        ("set_architect", "architect", "A. Architect"),
        ("set_customer", "customer", "C. Customer"),
        ("set_designer", "designer", "D. Designer"),
        ("set_deadline", "deadline", "2026-12-01"),
        ("set_description", "description", "A timber frame house"),
        ("set_address", "address", "Hauptstrasse 1"),
        ("set_postal_code", "postal_code", "6000"),
        ("set_city", "city", "Luzern"),
        ("set_country", "country", "Switzerland"),
    ],
)
def test_string_metadata_round_trips(setter: str, getter: str, value: str) -> None:
    project = Document().project
    getattr(project, setter)(value)
    assert getattr(project, getter) == value


@pytest.mark.parametrize(
    ("setter", "getter", "value"),
    [
        ("set_latitude", "latitude", 47.05),
        ("set_longitude", "longitude", 8.31),
        ("set_elevation", "elevation", 435.0),
    ],
)
def test_float_metadata_round_trips(setter: str, getter: str, value: float) -> None:
    project = Document().project
    getattr(project, setter)(value)
    assert getattr(project, getter) == value


def test_user_attributes_round_trip_by_index() -> None:
    project = Document().project
    project.set_user_attribute(1, "alpha")
    project.set_user_attribute(2, "beta")
    project.set_user_attribute_name(1, "Phase")

    assert project.user_attribute(1) == "alpha"
    assert project.user_attribute(2) == "beta"
    assert project.user_attribute_name(1) == "Phase"
    # unset index reads as empty, not an error
    assert project.user_attribute(99) == ""
    assert project.user_attribute_name(99) == ""


def test_project_data_store_round_trips() -> None:
    project = Document().project
    assert project.data_keys() == []

    project.set_data("origin", "import")
    project.set_data("revision", "3")
    assert project.data("origin") == "import"
    assert project.data("revision") == "3"
    assert set(project.data_keys()) == {"origin", "revision"}

    project.delete_data("origin")
    assert project.data("origin") == ""
    assert set(project.data_keys()) == {"revision"}


def test_repr_mentions_name_and_guid() -> None:
    project = Document().project
    project.set_name("House A")
    text = repr(project)
    assert "House A" in text
    assert "fake-project-guid" in text

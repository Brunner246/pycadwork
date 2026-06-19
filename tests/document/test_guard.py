"""``require_3dc_document`` fails fast outside a 3dc model; passes inside one.

Driven through the FakeProjectAdapter / FakeState — no running cadwork. The
predicate is purely the active 3d file name: non-empty and ending ``.3dc``.
"""

from __future__ import annotations

import pytest

from pycadwork.cadwork_adapter.types import CoverKind, DetailType
from pycadwork.detail import DetailDefinition, MemberSpec, build_detail
from pycadwork.document import (
    Document,
    NotA3dcDocumentError,
    is_3dc_document,
    require_3dc_document,
)
from pycadwork.geometry import AxisPoints, Point3D, RectSection
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def _wall_detail():
    return DetailDefinition(
        name="corner",
        detail_type=DetailType.CORNER_DETAIL,
        cover_kind=CoverKind.FRAMED_WALL,
        members=(
            MemberSpec(
                kind="beam",
                section=RectSection(60, 120),
                points=AxisPoints(
                    Point3D(0, 0, 0), Point3D(0, 0, 2500), Point3D(0, 1, 0)
                ),
                role="stud",
            ),
        ),
    )


def test_default_fake_is_a_3dc_document(fake_cadwork: FakeCadworkAdapter):
    # The fake defaults to a valid 3dc doc, so existing detail tests are unaffected.
    assert fake_cadwork.state.file_name_3dc.endswith(".3dc")
    assert is_3dc_document() is True
    assert Document().is_3dc() is True


def test_guard_allows_build_in_a_3dc_document(fake_cadwork: FakeCadworkAdapter):
    with require_3dc_document():
        result = build_detail(_wall_detail(), calculate=True)
    assert result.calculated
    assert len(result.member_ids) == 1


@pytest.mark.parametrize("name", ["plan.2dc", "", "MODEL.txt"])
def test_guard_raises_outside_a_3dc_document(
    fake_cadwork: FakeCadworkAdapter, name: str
):
    fake_cadwork.state.file_name_3dc = name
    assert is_3dc_document() is False

    with pytest.raises(NotA3dcDocumentError):
        with require_3dc_document():
            build_detail(_wall_detail())

    # Nothing was created — the guard tripped before any element work.
    assert fake_cadwork.state.elements == {}


def test_predicate_is_case_insensitive(fake_cadwork: FakeCadworkAdapter):
    fake_cadwork.state.file_name_3dc = "Model.3DC"
    assert is_3dc_document() is True

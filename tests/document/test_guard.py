"""``require_3d_document`` fails fast outside a 3D model; passes inside one.

Driven through the FakeProjectAdapter / FakeState — no running cadwork. The
predicate is purely the active 3D file name: non-empty and ending ``.3d`` or
``.3dc``.
"""

from __future__ import annotations

import pytest

from pycadwork.document import (
    Document,
    NotA3dDocumentError,
    is_3d_document,
    require_3d_document,
)
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def test_default_fake_is_a_3d_document(fake_cadwork: FakeCadworkAdapter):
    # The fake defaults to a valid 3D doc.
    assert fake_cadwork.state.model_file_name.endswith(".3dc")
    assert is_3d_document() is True
    assert Document().is_3d() is True


@pytest.mark.parametrize("name", ["model.3d", "Model.3dc", "C:/proj/Tower.3D"])
def test_both_3d_extensions_count(fake_cadwork: FakeCadworkAdapter, name: str):
    # A cadwork 3D model may be saved as either .3d or .3dc.
    fake_cadwork.state.model_file_name = name
    assert is_3d_document() is True
    assert Document().is_3d() is True


def test_guard_allows_the_body_in_a_3d_document(fake_cadwork: FakeCadworkAdapter):
    entered = False
    with require_3d_document():
        entered = True
    assert entered is True


@pytest.mark.parametrize("name", ["plan.2dc", "", "MODEL.txt"])
def test_guard_raises_outside_a_3d_document(
    fake_cadwork: FakeCadworkAdapter, name: str
):
    fake_cadwork.state.model_file_name = name
    assert is_3d_document() is False

    # The guard trips on entry, so the body never runs.
    entered = False
    with pytest.raises(NotA3dDocumentError):
        with require_3d_document():
            entered = True
    assert entered is False


def test_predicate_is_case_insensitive(fake_cadwork: FakeCadworkAdapter):
    fake_cadwork.state.model_file_name = "Model.3DC"
    assert is_3d_document() is True

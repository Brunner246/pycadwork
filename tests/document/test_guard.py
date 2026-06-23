"""``require_3dc_document`` fails fast outside a 3dc model; passes inside one.

Driven through the FakeProjectAdapter / FakeState — no running cadwork. The
predicate is purely the active 3d file name: non-empty and ending ``.3dc``.
"""

from __future__ import annotations

import pytest

from pycadwork.document import (
    Document,
    NotA3dcDocumentError,
    is_3dc_document,
    require_3dc_document,
)
from tests._fakes.cadwork_adapter import FakeCadworkAdapter


def test_default_fake_is_a_3dc_document(fake_cadwork: FakeCadworkAdapter):
    # The fake defaults to a valid 3dc doc.
    assert fake_cadwork.state.file_name_3dc.endswith(".3dc")
    assert is_3dc_document() is True
    assert Document().is_3dc() is True


def test_guard_allows_the_body_in_a_3dc_document(fake_cadwork: FakeCadworkAdapter):
    entered = False
    with require_3dc_document():
        entered = True
    assert entered is True


@pytest.mark.parametrize("name", ["plan.2dc", "", "MODEL.txt"])
def test_guard_raises_outside_a_3dc_document(
    fake_cadwork: FakeCadworkAdapter, name: str
):
    fake_cadwork.state.file_name_3dc = name
    assert is_3dc_document() is False

    # The guard trips on entry, so the body never runs.
    entered = False
    with pytest.raises(NotA3dcDocumentError):
        with require_3dc_document():
            entered = True
    assert entered is False


def test_predicate_is_case_insensitive(fake_cadwork: FakeCadworkAdapter):
    fake_cadwork.state.file_name_3dc = "Model.3DC"
    assert is_3dc_document() is True

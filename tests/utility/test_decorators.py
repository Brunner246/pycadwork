"""auto_repr / auto_eq / auto_hash / deprecated — pure-Python decorators."""
from __future__ import annotations

import pytest

from pycadwork import (
    AxisPoints,
    Beam,
    Point3D,
    RectSection,
    auto_eq,
    auto_hash,
    auto_repr,
    deprecated,
)


def _make_beam() -> Beam:
    return Beam.create_rectangular(
        RectSection(80.0, 200.0),
        AxisPoints(Point3D(0, 0, 0), Point3D(0, 1000, 0), Point3D(0, 0, 1)),
    )


# --------------------------------------------------------------------------- #
# auto_repr                                                                    #
# --------------------------------------------------------------------------- #
class TestAutoReprBare:
    def test_renders_public_slots_only(self):
        @auto_repr
        class Thing:
            __slots__ = ("a", "b", "_hidden")

            def __init__(self) -> None:
                self.a = 1
                self.b = "x"
                self._hidden = 99

        assert repr(Thing()) == "Thing(a=1, b='x')"

    def test_walks_mro_in_order_and_dedupes(self):
        class Base:
            __slots__ = ("a",)

        @auto_repr
        class Sub(Base):
            __slots__ = ("b",)

            def __init__(self) -> None:
                self.a = 1
                self.b = 2

        # Sub's own slots come first in MRO, then the base's.
        assert repr(Sub()) == "Sub(b=2, a=1)"

    def test_no_slots_renders_empty(self):
        class Base:
            __slots__ = ()

        @auto_repr
        class Empty(Base):
            __slots__ = ()

        assert repr(Empty()) == "Empty()"

    def test_unset_slot_renders_sentinel_without_raising(self):
        @auto_repr
        class Thing:
            __slots__ = ("a",)  # never assigned

        assert repr(Thing()) == "Thing(a=<unset>)"

    def test_bare_mode_never_invokes_a_property(self):
        calls: list[int] = []

        @auto_repr
        class Thing:
            __slots__ = ("a",)

            def __init__(self) -> None:
                self.a = 1

            @property
            def expensive(self) -> int:
                calls.append(1)
                raise AssertionError("property must not be touched")

        assert repr(Thing()) == "Thing(a=1)"
        assert calls == []


class TestAutoReprExplicit:
    def test_renders_named_attributes_with_repr(self):
        @auto_repr("a", "b")
        class Thing:
            __slots__ = ("a", "b")

            def __init__(self) -> None:
                self.a = 1
                self.b = "x"

        assert repr(Thing()) == "Thing(a=1, b='x')"

    def test_resolves_dotted_paths_and_properties_on_a_beam(self, fake_cadwork):
        beam = _make_beam()
        # Re-decorate the live Element class' repr is invasive; instead verify the
        # generated repr against a small wrapper using the same dotted resolution.
        @auto_repr("id", "attrs.name")
        class View:
            __slots__ = ("id", "attrs")

            def __init__(self, b: Beam) -> None:
                self.id = b.id
                self.attrs = b.attrs

        text = repr(View(beam))
        assert text == f"View(id={beam.id}, name='')"

    def test_property_error_renders_error_sentinel(self):
        @auto_repr("boom")
        class Thing:
            __slots__ = ()

            @property
            def boom(self) -> int:
                raise RuntimeError("backend down")

        assert repr(Thing()) == "Thing(boom=<error>)"


# --------------------------------------------------------------------------- #
# auto_eq / auto_hash                                                          #
# --------------------------------------------------------------------------- #
class TestAutoEq:
    def test_type_strict_equal_same_type(self):
        @auto_eq("v")
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        assert A(1) == A(1)
        assert A(1) != A(2)

    def test_type_strict_distinguishes_subclasses(self):
        @auto_eq("v")
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        class B(A):
            __slots__ = ()

        assert A(1) != B(1)
        assert (A(1) == B(1)) is False

    def test_foreign_type_is_not_equal(self):
        @auto_eq("v")
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        # __eq__ returns NotImplemented -> Python falls back to identity -> False.
        assert (A(1) == 5) is False

    def test_non_strict_matches_across_subclasses(self):
        @auto_eq("v", type_strict=False)
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        class B(A):
            __slots__ = ()

        assert A(1) == B(1)

    def test_eq_alone_makes_class_unhashable(self):
        @auto_eq("v")
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        with pytest.raises(TypeError):
            hash(A(1))


class TestAutoHash:
    def test_eq_and_hash_together_are_usable_as_keys(self):
        @auto_hash("v")
        @auto_eq("v")
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        assert hash(A(1)) == hash(A(1))
        assert len({A(1), A(1), A(2)}) == 2

    def test_hash_includes_type(self):
        @auto_hash("v")
        @auto_eq("v")
        class A:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        @auto_hash("v")
        @auto_eq("v")
        class B:
            __slots__ = ("v",)

            def __init__(self, v: int) -> None:
                self.v = v

        # Same field value, different type -> different hash bucket key.
        assert hash(A(1)) != hash(B(1))


# --------------------------------------------------------------------------- #
# deprecated                                                                   #
# --------------------------------------------------------------------------- #
class TestDeprecated:
    def test_emits_single_deprecation_warning(self):
        @deprecated("use new_fn instead", since="0.4", removal="1.0")
        def old_fn(x: int) -> int:
            return x * 2

        with pytest.warns(DeprecationWarning) as record:
            result = old_fn(21)

        assert result == 42
        assert len(record) == 1
        message = str(record[0].message)
        assert "old_fn is deprecated" in message
        assert "since 0.4" in message
        assert "removed in 1.0" in message
        assert "use new_fn instead" in message

    def test_forwards_args_and_kwargs(self):
        @deprecated("legacy")
        def f(a: int, b: int = 0, *, c: int = 0) -> int:
            return a + b + c

        with pytest.warns(DeprecationWarning):
            assert f(1, 2, c=3) == 6

    def test_preserves_wrapped_metadata(self):
        @deprecated("legacy")
        def documented() -> None:
            """Original docstring."""

        assert documented.__name__ == "documented"
        assert documented.__wrapped__ is not None
        assert "Original docstring." in (documented.__doc__ or "")
        assert ".. deprecated::" in (documented.__doc__ or "")

    def test_works_as_classmethod_when_outermost(self):
        class Widget:
            @classmethod
            @deprecated("use build")
            def make(cls) -> str:
                return cls.__name__

        with pytest.warns(DeprecationWarning):
            assert Widget.make() == "Widget"

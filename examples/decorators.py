"""Pure-Python class decorators — repr, value-equality, and deprecation.

``pycadwork.utility`` ships a handful of ``__slots__``-safe decorators that
remove boilerplate from wrapper classes. They import nothing from cadwork, so
everything here runs in any interpreter — there is no model, no adapter
involved (contrast :mod:`examples.utilities`, whose display helpers drive the
live cadwork seam).

* ``auto_repr``  — generate a never-raising ``__repr__``.
* ``auto_eq`` / ``auto_hash`` — structural value-equality and hashing.
* ``deprecated`` — emit a ``DeprecationWarning`` and annotate the docstring.

    uv run python -m examples.decorators
"""

from __future__ import annotations

import warnings

from pycadwork import auto_eq, auto_hash, auto_repr, deprecated


def demo_auto_repr_bare() -> None:
    """Bare ``@auto_repr`` discovers public slots and renders their direct values.

    It never invokes a ``@property`` — safe on wrapper classes whose properties
    run live backend queries — and leading-underscore slots are skipped.
    """

    @auto_repr
    class Section:
        __slots__ = ("width", "height", "_cached")

        def __init__(self, width: float, height: float) -> None:
            self.width = width
            self.height = height
            self._cached = object()  # private — never appears in the repr

    print(
        "bare repr =", repr(Section(120.0, 240.0))
    )  # Section(width=120.0, height=240.0)

    # A declared-but-unset slot renders <unset> instead of raising.
    unset = Section.__new__(Section)
    print("unset repr =", repr(unset))  # Section(width=<unset>, height=<unset>)


def demo_auto_repr_fields() -> None:
    """Field form renders exactly the named attributes — dotted paths and properties.

    This mirrors how the element wrappers expose an id plus a nested component
    (``element.attrs.name``); the field form opts in to resolving those.
    """

    class Attrs:
        __slots__ = ("name",)

        def __init__(self, name: str) -> None:
            self.name = name

    @auto_repr("id", "attrs.name")
    class View:
        __slots__ = ("id", "attrs")

        def __init__(self, eid: int, name: str) -> None:
            self.id = eid
            self.attrs = Attrs(name)

    print("field repr =", repr(View(42, "Stud-01")))  # View(id=42, name='Stud-01')


def demo_value_equality_and_hashing() -> None:
    """``auto_hash`` (outer) over ``auto_eq`` (inner) gives value-equality + hashing."""

    @auto_hash("x", "y")
    @auto_eq("x", "y")  # inner: defines __eq__ and nulls __hash__
    class Pixel:
        __slots__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    print("equal by value?", Pixel(1, 2) == Pixel(1, 2))  # True
    print("differ by value?", Pixel(1, 2) == Pixel(3, 4))  # False
    print("usable in a set:", len({Pixel(1, 2), Pixel(1, 2), Pixel(3, 4)}))  # 2

    # type_strict (the default) means a different class is never equal, even with
    # identical fields — matching Element's (type, id) rule.
    @auto_eq("x", "y")
    class Point:
        __slots__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    print("strict across types?", Pixel(1, 2) == Point(1, 2))  # False


def demo_deprecated() -> None:
    """`@deprecated` emits a DeprecationWarning on call and annotates the docstring."""

    @deprecated("use new_api instead", since="0.4", removal="1.0")
    def old_api() -> str:
        """Do the old thing."""
        return "result"

    # Calling it warns the *caller*; capture the warning to show its message.
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = old_api()

    print("still returns   =", result)  # the wrapped function still runs
    print("warning class   =", caught[0].category.__name__)  # DeprecationWarning
    print("warning message =", str(caught[0].message))
    print("docstring note  =", old_api.__doc__.splitlines()[0])  # .. deprecated:: 0.4


def run() -> None:
    """Run every decorator demo in order."""
    demo_auto_repr_bare()
    demo_auto_repr_fields()
    demo_value_equality_and_hashing()
    demo_deprecated()


if __name__ == "__main__":
    run()

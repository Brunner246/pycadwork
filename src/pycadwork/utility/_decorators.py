"""General-purpose class/function decorators above the cadwork_adapter seam.

All decorators here are ``__slots__``-safe and import nothing from cadwork — they
are pure-Python helpers that remove boilerplate from the wrapper classes:

* :func:`auto_repr` — generate a ``__repr__`` (slot-aware, never triggers a live
  backend query unless a property is named explicitly).
* :func:`auto_eq` / :func:`auto_hash` — structural value-equality / hashing for
  logically-immutable value objects.
* :func:`deprecated` — emit a ``DeprecationWarning`` on call; the package will
  rename and relocate APIs as it tracks cwapi3d versions.
"""

from __future__ import annotations

import warnings
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, overload

_T = TypeVar("_T", bound=type)
_R = TypeVar("_R")

# Sentinels rendered by ``auto_repr`` instead of raising — a ``__repr__`` that
# raises turns every debugger/pytest frame into a second error.
_UNSET = "<unset>"
_ERROR = "<error>"


# --------------------------------------------------------------------------- #
# auto_repr                                                                    #
# --------------------------------------------------------------------------- #
def _iter_mro_slots(cls: type) -> list[str]:
    """Public slot names declared across ``cls``'s MRO, in MRO order, deduped.

    Leading-underscore names (private state, name-mangled attrs) are skipped so
    the generated repr stays at the user-facing surface.
    """
    seen: set[str] = set()
    names: list[str] = []
    for klass in cls.__mro__:
        if klass is object:
            continue
        raw = klass.__dict__.get("__slots__", ())
        if isinstance(raw, str):
            raw = (raw,)
        for name in raw:
            if name.startswith("_") or name in seen:
                continue
            seen.add(name)
            names.append(name)
    return names


def _resolve(obj: object, dotted: str) -> Any:
    """Resolve a possibly dotted attribute path (``"attrs.name"``) via getattr."""
    value: Any = obj
    for part in dotted.split("."):
        value = getattr(value, part)
    return value


def _make_repr(field_specs: list[str]) -> Callable[[object], str]:
    def __repr__(self: object) -> str:
        parts: list[str] = []
        for spec in field_specs:
            label = spec.rsplit(".", 1)[-1]
            try:
                value = _resolve(self, spec)
            except AttributeError:
                parts.append(f"{label}={_UNSET}")
            except Exception:  # a repr must never raise — surface, don't crash
                parts.append(f"{label}={_ERROR}")
            else:
                parts.append(f"{label}={value!r}")
        return f"{type(self).__name__}({', '.join(parts)})"

    return __repr__


@overload
def auto_repr(cls: _T, /) -> _T: ...
@overload
def auto_repr(*fields: str) -> Callable[[_T], _T]: ...


def auto_repr(*args: Any) -> Any:
    """Generate a ``__slots__``-safe ``__repr__`` rendering ``Name(a=.., b=..)``.

    Two forms:

    * ``@auto_repr`` (bare) — auto-discover the **public** slots across the MRO and
      render their *direct* values. This never invokes a ``@property``, so it is
      safe on wrapper classes whose properties run live backend queries.
    * ``@auto_repr("id", "attrs.name")`` — render exactly the named attributes via
      ``getattr``. Dotted paths and ``@property`` are resolved, so this form is the
      opt-in way to include live-queried values (the caller accepts the cost).

    Values are formatted with ``!r``. A declared-but-unset slot renders ``<unset>``;
    any other resolution error renders ``<error>`` — the repr itself never raises.
    """
    # Bare ``@auto_repr`` — called with the class itself.
    if len(args) == 1 and isinstance(args[0], type):
        cls = args[0]
        cls.__repr__ = _make_repr(_iter_mro_slots(cls))  # type: ignore[method-assign]
        return cls

    # ``@auto_repr("a", "b")`` — called with field names, returns the decorator.
    fields = list(args)

    def decorate(cls: _T) -> _T:
        cls.__repr__ = _make_repr(fields or _iter_mro_slots(cls))  # type: ignore[method-assign]
        return cls

    return decorate


# --------------------------------------------------------------------------- #
# auto_eq / auto_hash                                                          #
# --------------------------------------------------------------------------- #
def auto_eq(*fields: str, type_strict: bool = True) -> Callable[[_T], _T]:
    """Generate ``__eq__`` comparing the named fields (read via ``getattr``).

    With ``type_strict`` (the default) two instances are equal only when
    ``type(self) is type(other)`` — matching ``Element``'s ``(type, id)`` rule, so
    a ``Beam`` never equals a ``Plate`` even with identical fields. Set
    ``type_strict=False`` to compare across a class and its subclasses.

    Comparison against a foreign type returns ``NotImplemented`` (Python then tries
    the reflected operand and ultimately falls back to identity).

    This uses **exact** ``==`` on each field — do not apply it to the geometry value
    objects (``Point3D``/``Vector3D``), whose epsilon-tolerant equality is
    deliberate. Defining ``__eq__`` sets ``__hash__`` to ``None``; pair this with
    :func:`auto_hash` over the same fields if instances must stay hashable.
    """
    names = tuple(fields)

    def decorate(cls: _T) -> _T:
        def __eq__(self: object, other: object) -> bool:
            if type_strict:
                if type(self) is not type(other):
                    return NotImplemented
            elif not isinstance(other, cls):
                return NotImplemented
            return all(getattr(self, n) == getattr(other, n) for n in names)

        cls.__eq__ = __eq__  # type: ignore[method-assign]
        # Python nulls __hash__ when __eq__ is defined in a class body, but NOT
        # when it is assigned afterwards. Do it ourselves so a value-equal class
        # is not left hashing by identity (which breaks the hash/eq invariant).
        cls.__hash__ = None  # type: ignore[assignment]
        return cls

    return decorate


def auto_hash(*fields: str) -> Callable[[_T], _T]:
    """Generate ``__hash__`` over ``(type(self), *fields)``.

    Pair with :func:`auto_eq` over the **same** fields, applied as the *outer*
    decorator so it runs after ``auto_eq`` (which nulls ``__hash__``)::

        @auto_hash("v")
        @auto_eq("v")
        class V: ...

    Only for logically immutable value objects — hashing mutable state breaks
    dict/set invariants.
    """
    names = tuple(fields)

    def decorate(cls: _T) -> _T:
        def __hash__(self: object) -> int:
            return hash((type(self), *(getattr(self, n) for n in names)))

        cls.__hash__ = __hash__  # type: ignore[method-assign]
        return cls

    return decorate


# --------------------------------------------------------------------------- #
# deprecated                                                                   #
# --------------------------------------------------------------------------- #
def deprecated(
    reason: str, *, since: str | None = None, removal: str | None = None
) -> Callable[[Callable[..., _R]], Callable[..., _R]]:
    """Mark a callable deprecated; emit a ``DeprecationWarning`` on each call.

    ``since`` and ``removal`` are woven into the warning message and prepended to
    the wrapped callable's ``__doc__`` as a ``.. deprecated::`` note. The warning
    points at the *caller* (``stacklevel=2``).

    For a classmethod, apply ``@classmethod`` as the outermost decorator::

        @classmethod
        @deprecated("use create_rectangular", since="0.4", removal="1.0")
        def create_rect(cls, ...): ...
    """

    def decorate(func: Callable[..., _R]) -> Callable[..., _R]:
        bits = [f"{func.__qualname__} is deprecated"]
        if since:
            bits.append(f"since {since}")
        if removal:
            bits.append(f"and will be removed in {removal}")
        message = f"{' '.join(bits)}: {reason}"

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> _R:
            warnings.warn(message, category=DeprecationWarning, stacklevel=2)
            return func(*args, **kwargs)

        note = f".. deprecated:: {since or ''}\n    {reason}"
        wrapper.__doc__ = f"{note}\n\n{func.__doc__}" if func.__doc__ else note
        return wrapper

    return decorate

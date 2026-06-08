"""The canonical home for pycadwork's typed value aliases.

Every other module imports its identity and measurement types from here. This
is a *leaf* module — it imports only :func:`typing.NewType` and nothing from
``pycadwork``, so no import cycle is possible no matter who depends on it.

These are :func:`typing.NewType` aliases, **not** classes. At runtime an
``ElementId`` *is* the ``int`` it wraps and a ``Length`` *is* the ``float`` it
wraps, so all existing arithmetic, comparisons, setters, SQLite round-trips,
and tests keep working untouched and at zero overhead — only the static
annotations change. A ``Length`` is assignable to a plain ``float`` parameter
(the correct direction for outward-flowing return values); only the reverse,
``float -> Length``, needs an explicit wrap, which happens exactly at the
return sites that hand back a value whose meaning is known.

Two kinds of value are wrapped:

* **Identities.** A type checker rejects passing a ``ProjectGuid`` where a
  ``CadworkGuid`` belongs, or transposing the ``(container_id, member_id)``
  pair — the positional mix-ups bare ``str`` / ``int`` fields silently invite.
  ``ContainerId`` and ``MemberId`` layer on ``ElementId`` — a container and a
  member are both elements — so either is accepted where an ``ElementId`` is
  expected while remaining mutually distinct.
* **Measurements.** A ``Length`` is not a ``Volume`` is not an ``Angle``;
  wrapping the physical-quantity return sites keeps these from being silently
  confused, and makes signatures self-documenting.

Only *identity* and *physical measurement* are wrapped. Free-text descriptive
strings (``name``, ``comment``, ``material_name``, ``group``, ``part_number``,
…) and dimensionless / derived scalars (squared distances, dot products,
parameters, plane coefficients, counts, geo-coordinates) stay primitive:
wrapping them would be noise.
"""

from __future__ import annotations

from typing import NewType

# ---- identities ----
ElementId = NewType("ElementId", int)
ProjectGuid = NewType("ProjectGuid", str)
CadworkGuid = NewType("CadworkGuid", str)
ContainerId = NewType("ContainerId", ElementId)
MemberId = NewType("MemberId", ElementId)

# ---- measurements ----
# Defined only for quantities with a real return site today; ``Area`` is
# intentionally omitted until an area accessor lands.
Length = NewType("Length", float)
Width = NewType("Width", float)
Height = NewType("Height", float)
Thickness = NewType("Thickness", float)
Diameter = NewType("Diameter", float)
Radius = NewType("Radius", float)
Volume = NewType("Volume", float)
Weight = NewType("Weight", float)
Distance = NewType("Distance", float)
Angle = NewType("Angle", float)  # radians, matches Vector3D / Plane3D.angle_to

__all__ = [
    "Angle",
    "CadworkGuid",
    "ContainerId",
    "Diameter",
    "Distance",
    "ElementId",
    "Height",
    "Length",
    "MemberId",
    "ProjectGuid",
    "Radius",
    "Thickness",
    "Volume",
    "Weight",
    "Width",
]

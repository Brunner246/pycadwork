"""Value objects for the sphere-pavilion build.

:class:`StrutGroup` is the fabrication deliverable behind "make the members as
equal as possible": a projected geodesic sphere has struts in a few discrete
length classes, and this bins them so the shop sees "Strut A ×30, Strut B ×60".
:class:`SpherePavilionResult` is what :meth:`SpherePavilionBuilder.build` returns
— mirrors :class:`~pycadwork.gridshell.specs.GridShellResult` but adds the strut
schedule and carries members and cladding together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycadwork.element.beam import Beam
    from pycadwork.element.plate import Plate
    from pycadwork.gridshell.specs import GridNode


@dataclass(frozen=True, slots=True)
class StrutGroup:
    """One length-class of struts (a fabrication "Strut A / B / C").

    ``member_indices`` index into :attr:`SpherePavilionResult.members` (which is
    aligned with the deduplicated lattice edges), so the shop can map a length
    class back to the exact struts. ``nominal_length`` is the class's average
    chord length; base struts trimmed by the ground cut are physically shorter
    than the nominal but still reported under their class.
    """

    nominal_length: float
    count: int
    member_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SpherePavilionResult:
    """What a sphere-pavilion build produced, plus any non-fatal warnings.

    ``members`` are the dome struts (the base-ring edges are excluded — they
    become ``ring``). ``ring`` is the closed sill band of horizontal beams at the
    ground cut; ``foundation`` is the slab the dome sits on (``None`` unless a
    foundation was requested). Both are empty/``None`` for an untruncated sphere.
    """

    members: tuple["Beam", ...] = ()
    panels: tuple["Plate", ...] = ()
    ring: tuple["Beam", ...] = ()
    foundation: "Plate | None" = None
    strut_groups: tuple[StrutGroup, ...] = ()
    nodes: tuple["GridNode", ...] = ()
    warnings: tuple[str, ...] = field(default_factory=tuple)

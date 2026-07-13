"""GridShellBuilder: a fluent builder that turns triangulated surfaces into a
beam lattice or a panel shell.

Mirrors :class:`~pycadwork.element.cover.builder.CoverBuilder`: the constructor
takes the input, config methods return ``self``, and a terminal :meth:`build`
validates that a mode was chosen (``ValueError`` otherwise) before dispatching
the chosen strategy over the extracted :class:`GridTopology`.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from pycadwork.element.surface import Surface
from pycadwork.gridshell.joints.hub import HubConnectorJoint
from pycadwork.gridshell.joints.miter import MiterJoint
from pycadwork.gridshell.laths import build_laths
from pycadwork.gridshell.members import build_members
from pycadwork.gridshell.panels import build_panels
from pycadwork.gridshell.specs import (
    GridShellResult,
    HubJoint,
    MiterPolicy,
    TrimPolicy,
)
from pycadwork.gridshell.topology import GridTopology

if TYPE_CHECKING:
    from pycadwork.geometry import Point3D, RectSection
    from pycadwork.gridshell.joints.base import JointStrategy
    from pycadwork.value_types import Thickness


class GridShellBuilder:
    """Assemble a gridshell (members or panels) from triangulated surfaces."""

    def __init__(self, surfaces: Surface | Sequence[Surface]) -> None:
        self._surfaces = [surfaces] if isinstance(surfaces, Surface) else list(surfaces)
        self._grid: list[list["Point3D"]] | None = None
        self._build: Callable[[], GridShellResult] | None = None
        self._tolerance = 1e-6
        self._strict = True
        self._miter = MiterPolicy.VALENCE_2_ONLY
        self._trim = TrimPolicy.NONE
        self._joint: HubJoint | None = None
        self._joint_strategy: "JointStrategy | None" = None

    @classmethod
    def from_grid(cls, grid: "Sequence[Sequence[Point3D]]") -> "GridShellBuilder":
        """Build from a sample grid instead of surfaces (required for ``laths``).

        The grid's rows and columns are the two lath families. ``members`` /
        ``panels`` need triangulated surfaces, so use the surface constructor
        for those; ``laths`` needs the raw grid, so use this.
        """
        builder = cls([])
        builder._grid = [list(row) for row in grid]
        return builder

    # ---- mode selection (sets the strategy) ----

    def members(self, section: "RectSection") -> "GridShellBuilder":
        """Build a beam lattice with the given rectangular cross-section."""

        def strategy() -> GridShellResult:
            return build_members(
                self._topology(),
                section,
                strategy=self._resolve_joint(),
                trim=self._trim,
            )

        self._build = strategy
        return self

    def _topology(self) -> GridTopology:
        breps = [surface.geometry.brep for surface in self._surfaces]
        return GridTopology.from_breps(
            breps, tolerance=self._tolerance, strict=self._strict
        )

    def _resolve_joint(self) -> "JointStrategy":
        """The joint strategy for a members build.

        An explicit :meth:`joint` wins. Otherwise the legacy ``miter_policy`` /
        ``hub_joints`` flags are composed into the equivalent strategy so old
        call sites keep their exact behaviour.
        """
        if self._joint_strategy is not None:
            return self._joint_strategy
        if self._joint is not None:
            return HubConnectorJoint(
                gap=self._joint.gap,
                min_valence=self._joint.min_valence,
                miter_policy=self._miter,
            )
        return MiterJoint(self._miter)

    def panels(self, thickness: "float | Thickness") -> "GridShellBuilder":
        """Build a panel shell of the given thickness.

        The flat triangular panels tile the surface directly, one per face.
        """

        def strategy() -> GridShellResult:
            return build_panels(self._topology(), float(thickness))

        self._build = strategy
        return self

    def laths(
        self,
        section: "RectSection",
        *,
        layers: int = 2,
        layer_gap: float,
        bolt_diameter: float | None = None,
    ) -> "GridShellBuilder":
        """Build a double-layer lath gridshell (requires :meth:`from_grid`).

        Two families of continuous laths — one along the grid rows, one along the
        columns — are stacked ``layer_gap`` apart along the shell normal and
        bolted where they cross. Continuous laths pass straight through the
        interior nodes, so there is no multi-rib hub joint to solve.
        """
        if self._grid is None:
            raise ValueError(
                "GridShellBuilder.laths: no grid; "
                "construct with GridShellBuilder.from_grid(...) for lath mode"
            )
        grid = self._grid

        def strategy() -> GridShellResult:
            return build_laths(
                grid,
                section,
                layers=layers,
                layer_gap=layer_gap,
                bolt_diameter=bolt_diameter,
            )

        self._build = strategy
        return self

    # ---- shared config (return self) ----

    def with_tolerance(self, tolerance: float) -> "GridShellBuilder":
        """Vertex-merge tolerance for stitching shared triangle vertices."""
        self._tolerance = tolerance
        return self

    def lenient(self, lenient: bool = True) -> "GridShellBuilder":
        """Skip (and warn about) non-triangular/degenerate faces instead of raising."""
        self._strict = not lenient
        return self

    def joint(self, strategy: "JointStrategy") -> "GridShellBuilder":
        """Set the node-joint strategy for a members build (members mode only).

        This is the general entry point: pass a
        :class:`~pycadwork.gridshell.joints.base.JointStrategy` such as
        :class:`~pycadwork.gridshell.joints.hub.HubConnectorJoint`,
        :class:`~pycadwork.gridshell.joints.radial.RadialMiterJoint`, or
        :class:`~pycadwork.gridshell.joints.lap.LapJoint`. An explicit strategy
        overrides the legacy :meth:`miter_policy` / :meth:`hub_joints` flags.
        """
        self._joint_strategy = strategy
        return self

    def miter_policy(self, policy: MiterPolicy) -> "GridShellBuilder":
        """Choose how beams meeting at a node are mitered (members mode only).

        Legacy convenience for the common miter case; equivalent to
        ``joint(MiterJoint(policy))``. Ignored when an explicit :meth:`joint` is set.
        """
        self._miter = policy
        return self

    def hub_joints(self, gap: float, *, min_valence: int = 3) -> "GridShellBuilder":
        """Trim ribs back from multi-rib nodes by ``gap`` (members mode only).

        Legacy convenience: composes with :meth:`miter_policy` into a
        :class:`~pycadwork.gridshell.joints.hub.HubConnectorJoint` (setback only,
        no connector). For a connector-filled or dowelled hub, pass a configured
        ``HubConnectorJoint`` to :meth:`joint` instead. Ignored when an explicit
        :meth:`joint` is set.

        Every rib incident to a node of valence ``>= min_valence`` is shortened
        by ``gap`` at that end, so each rib becomes a producible straight stick
        with flat end cuts. Genuine two-rib corners still miter. The setback
        shortens the axis at creation; it is not a boolean cut.
        """
        self._joint = HubJoint(gap=float(gap), min_valence=min_valence)
        return self

    def seat_on_surface(
        self, policy: TrimPolicy = TrimPolicy.SEAT_ON_SURFACE
    ) -> "GridShellBuilder":
        """Seat ribs flush on the shell by offsetting them (members mode only).

        This offsets each rib below the surface by half its height at creation;
        it is not a boolean cut.
        """
        self._trim = policy
        return self

    # ---- terminal ----

    def build(self) -> GridShellResult:
        """Run the chosen strategy (extracting topology from the inputs if needed)."""
        if self._build is None:
            raise ValueError(
                "GridShellBuilder.build: no mode set; "
                "call members(...), panels(...), or laths(...) first"
            )
        return self._build()

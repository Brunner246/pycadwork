"""Element wrappers — typed views over cadwork IDs."""
from __future__ import annotations

from pycadwork.element.auxiliary import AuxiliaryElement
from pycadwork.element.base import Element
from pycadwork.element.beam import Beam, CrossSection
from pycadwork.element.connector_axis import ConnectorAxis
from pycadwork.element.drilling import Drilling
from pycadwork.element.factory import from_id
from pycadwork.element.linear import LinearElement
from pycadwork.element.node import Line, Node
from pycadwork.element.opening import Opening
from pycadwork.element.oriented import OrientedElement
from pycadwork.element.plate import Plate
from pycadwork.element.registry import REGISTRY, ElementRegistry, register_element
from pycadwork.element.surface import Surface

# Cover aggregates (Wall / Slab / Roof) live in the element.cover subpackage and
# self-register via @register_element, exactly like the primitive wrappers imported
# above. Importing the subpackage here makes that registration eager: by the time
# anything can reach from_id, pycadwork.element has finished importing and the
# dispatch table is already complete. Must come after base/registry/factory above —
# the cover modules depend on them.
from pycadwork.element import cover  # noqa: F401

__all__ = [
    "REGISTRY",
    "AuxiliaryElement",
    "Beam",
    "ConnectorAxis",
    "CrossSection",
    "Drilling",
    "Element",
    "ElementRegistry",
    "Line",
    "LinearElement",
    "Node",
    "Opening",
    "OrientedElement",
    "Plate",
    "Surface",
    "from_id",
    "register_element",
]

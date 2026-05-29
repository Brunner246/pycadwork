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

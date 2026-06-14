"""pycadwork.detail — author, serialize, share, and realize element-module details.

A *detail* is a parametric timber-frame situation (a corner, a T-junction, an
opening, …) that cadwork's element module expands into real framing inside a
wall/floor/roof. This package splits cleanly into two layers:

* a **pure definition layer** — :class:`DetailDefinition` and friends, frozen and
  stdlib-only, fully serializable and testable with no cadwork present. This is
  the shareable schema. Author it fluently with :class:`DetailBuilder`, describe
  member semantics with named :mod:`roles`, and (de)serialize it through
  :func:`load_definition` (native + foreign schemas via the loader seam);
* a **realizer** — :func:`build_detail`, the only part that reaches the model. It
  creates the members, anchors them on a host cover, applies each member's
  :class:`ModuleProperties`, and runs the calculation, all through the
  version-isolation seam.

Importing this package also registers the bundled loaders (native + the worked
foreign example), so :func:`load_definition` is ready immediately.
"""

from __future__ import annotations

from pycadwork.cadwork_adapter.types import DetailType
from pycadwork.detail.builder import DetailBuilder, required_kinds
from pycadwork.detail.definition import (
    NATIVE_SCHEMA,
    NATIVE_VERSION,
    DefinitionError,
    DetailDefinition,
    MemberSpec,
)
from pycadwork.detail.loader import (
    DefinitionLoader,
    LoaderRegistry,
    UnknownSchemaError,
    load_definition,
    register_loader,
)
from pycadwork.detail.properties import (
    CuttingElement,
    Distribution,
    ModuleProperties,
    ModulePropertyError,
    NamedFlag,
)
from pycadwork.detail.realizer import (
    DetailResult,
    build_detail,
    run_calculation,
    save_detail,
    set_detail_path,
)
from pycadwork.detail.roles import (
    SemanticRole,
    UnknownRoleError,
    get_role,
    register_role,
    resolve,
    role_names,
)

# Registers the bundled loaders (native + worked foreign example) on import.
from pycadwork.detail import loaders as _loaders  # noqa: F401

__all__ = [
    "CuttingElement",
    "DefinitionError",
    "DefinitionLoader",
    "DetailBuilder",
    "DetailDefinition",
    "DetailResult",
    "DetailType",
    "Distribution",
    "LoaderRegistry",
    "MemberSpec",
    "ModuleProperties",
    "ModulePropertyError",
    "NATIVE_SCHEMA",
    "NATIVE_VERSION",
    "NamedFlag",
    "SemanticRole",
    "UnknownRoleError",
    "UnknownSchemaError",
    "build_detail",
    "get_role",
    "load_definition",
    "register_loader",
    "register_role",
    "required_kinds",
    "resolve",
    "role_names",
    "run_calculation",
    "save_detail",
    "set_detail_path",
]

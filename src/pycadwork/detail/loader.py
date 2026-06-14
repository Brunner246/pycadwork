"""The loader seam: turn a foreign or native raw dict into a ``DetailDefinition``.

A definition shared from elsewhere need not be in pycadwork's own JSON shape. A
:class:`DefinitionLoader` translates one external *schema* (identified by a
``schema`` string and one or more ``schema_version`` values) into the internal
:class:`DetailDefinition`. Loaders register themselves with
:func:`register_loader`; :func:`load_definition` reads the ``schema`` /
``schema_version`` off a raw payload and dispatches to the matching loader.

A loader registered for version ``"*"`` is the fallback for its schema — used
when no exact version match exists, so a schema can opt into "any version" with
one registration. This is the documented extension point: third-party schemas
are supported by writing and registering a loader, never by editing this module.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pycadwork.detail.definition import DetailDefinition


class UnknownSchemaError(KeyError):
    """Raised when no loader is registered for a payload's (schema, version)."""


@runtime_checkable
class DefinitionLoader(Protocol):
    """Translates one external schema into a :class:`DetailDefinition`."""

    @property
    def schema(self) -> str: ...

    @property
    def versions(self) -> tuple[str, ...]: ...

    def load(self, raw: dict[str, Any]) -> DetailDefinition: ...


class LoaderRegistry:
    """A table mapping ``(schema, version)`` to a :class:`DefinitionLoader`."""

    __slots__ = ("_loaders",)

    def __init__(self) -> None:
        self._loaders: dict[tuple[str, str], DefinitionLoader] = {}

    def register(self, loader: DefinitionLoader) -> None:
        for version in loader.versions:
            self._loaders[(loader.schema, version)] = loader

    def resolve(self, schema: str, version: str) -> DefinitionLoader:
        """Find the loader for ``(schema, version)``, falling back to ``"*"``."""
        loader = self._loaders.get((schema, version)) or self._loaders.get(
            (schema, "*")
        )
        if loader is None:
            raise UnknownSchemaError(
                f"no loader for schema={schema!r} version={version!r}"
            )
        return loader

    def load(self, raw: dict[str, Any]) -> DetailDefinition:
        schema = raw.get("schema")
        if not schema:
            raise UnknownSchemaError("payload has no 'schema' key")
        version = str(raw.get("schema_version", "*"))
        return self.resolve(schema, version).load(raw)


#: The package-wide loader registry consulted by :func:`load_definition`.
REGISTRY = LoaderRegistry()


def register_loader(cls: type) -> type:
    """Class decorator: instantiate ``cls`` and register it in :data:`REGISTRY`.

    ``cls`` must satisfy the :class:`DefinitionLoader` protocol (a ``schema``,
    ``versions``, and ``load``). Registration happens at import::

        @register_loader
        class MyLoader:
            schema = "vendor.frames"
            versions = ("1", "*")
            def load(self, raw): ...
    """
    REGISTRY.register(cls())
    return cls


def load_definition(raw: dict[str, Any]) -> DetailDefinition:
    """Dispatch ``raw`` to the loader matching its ``schema`` / ``schema_version``."""
    return REGISTRY.load(raw)

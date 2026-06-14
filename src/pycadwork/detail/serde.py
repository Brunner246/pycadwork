"""Geometry/spec (de)serialization for detail definitions.

The geometry value-types (:class:`Point3D`, :class:`Vector3D`) and the creation
specs (:class:`RectSection`, :class:`PanelSection`, :class:`AxisPoints`,
:class:`AxisFrame`) carry no serialization methods of their own — keeping the
``geometry`` package free of JSON concerns. Instead this module owns two small
dispatch tables:

* **encoders** keyed by Python type, each emitting a plain ``dict`` tagged with
  a ``"$type"`` discriminator;
* **decoders** keyed by that discriminator string.

The discriminator is load-bearing: :class:`RectSection` (``width``/``height``)
and :class:`PanelSection` (``width``/``thickness``) are structurally similar, as
are :class:`AxisPoints` and :class:`AxisFrame` — only the tag tells them apart.
The loaders reuse these helpers, so a foreign schema that maps onto the internal
specs serializes identically to a native one.
"""

from __future__ import annotations

from typing import Any, Callable

from pycadwork.geometry.point3d import Point3D
from pycadwork.geometry.specs import (
    AxisFrame,
    AxisPoints,
    PanelSection,
    RectSection,
)
from pycadwork.geometry.vector3d import Vector3D


class SerdeError(ValueError):
    """Raised when a geometry/spec payload cannot be (de)serialized."""


# ---- encoders (Python type -> tagged dict) ----


def _enc_point(p: Point3D) -> dict[str, Any]:
    return {"$type": "Point3D", "x": p.x, "y": p.y, "z": p.z}


def _enc_vector(v: Vector3D) -> dict[str, Any]:
    return {"$type": "Vector3D", "x": v.x, "y": v.y, "z": v.z}


def _enc_rect(s: RectSection) -> dict[str, Any]:
    return {"$type": "RectSection", "width": s.width, "height": s.height}


def _enc_panel(s: PanelSection) -> dict[str, Any]:
    return {"$type": "PanelSection", "width": s.width, "thickness": s.thickness}


def _enc_axis_points(a: AxisPoints) -> dict[str, Any]:
    return {
        "$type": "AxisPoints",
        "p1": _enc_point(a.p1),
        "p2": _enc_point(a.p2),
        "p3": _enc_point(a.p3),
    }


def _enc_axis_frame(a: AxisFrame) -> dict[str, Any]:
    return {
        "$type": "AxisFrame",
        "origin": _enc_point(a.origin),
        "x_dir": _enc_vector(a.x_dir),
        "z_dir": _enc_vector(a.z_dir),
        "length": a.length,
    }


_ENCODERS: dict[type, Callable[[Any], dict[str, Any]]] = {
    Point3D: _enc_point,
    Vector3D: _enc_vector,
    RectSection: _enc_rect,
    PanelSection: _enc_panel,
    AxisPoints: _enc_axis_points,
    AxisFrame: _enc_axis_frame,
}


# ---- decoders ("$type" -> object) ----


def _dec_point(d: dict[str, Any]) -> Point3D:
    return Point3D(float(d["x"]), float(d["y"]), float(d["z"]))


def _dec_vector(d: dict[str, Any]) -> Vector3D:
    return Vector3D(float(d["x"]), float(d["y"]), float(d["z"]))


def _dec_rect(d: dict[str, Any]) -> RectSection:
    return RectSection(float(d["width"]), float(d["height"]))


def _dec_panel(d: dict[str, Any]) -> PanelSection:
    return PanelSection(float(d["width"]), float(d["thickness"]))


def _dec_axis_points(d: dict[str, Any]) -> AxisPoints:
    return AxisPoints(_dec_point(d["p1"]), _dec_point(d["p2"]), _dec_point(d["p3"]))


def _dec_axis_frame(d: dict[str, Any]) -> AxisFrame:
    return AxisFrame(
        _dec_point(d["origin"]),
        _dec_vector(d["x_dir"]),
        _dec_vector(d["z_dir"]),
        float(d["length"]),
    )


_DECODERS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "Point3D": _dec_point,
    "Vector3D": _dec_vector,
    "RectSection": _dec_rect,
    "PanelSection": _dec_panel,
    "AxisPoints": _dec_axis_points,
    "AxisFrame": _dec_axis_frame,
}


def encode(obj: Any) -> dict[str, Any]:
    """Encode a geometry value or creation spec to a ``$type``-tagged dict."""
    encoder = _ENCODERS.get(type(obj))
    if encoder is None:
        raise SerdeError(f"no encoder for {type(obj).__name__}")
    return encoder(obj)


def decode(data: dict[str, Any]) -> Any:
    """Decode a ``$type``-tagged dict back to its geometry value or spec."""
    try:
        tag = data["$type"]
    except (KeyError, TypeError):
        raise SerdeError(f"payload has no $type discriminator: {data!r}") from None
    decoder = _DECODERS.get(tag)
    if decoder is None:
        raise SerdeError(f"unknown $type {tag!r}")
    return decoder(data)

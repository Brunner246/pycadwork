"""my-plugin — a cadwork plugin entry point built on pycadwork.

Two environments, one source file:

* **Development** (this uv project): `uv sync` gives your IDE autocompletion and
  type-checking for `pycadwork` (and `cwapi3d`), and `uv run pytest` runs your
  unit tests. You do *not* run `main()` here — it talks to the live model, which
  only exists inside cadwork. Keep pure, testable logic in your own modules and
  exercise it under pytest; keep `main()` a thin shell that wires it to cadwork.

* **Runtime** (inside cadwork): copy this file into your cadwork userprofile API
  folder, e.g. ``<userprofile>\\<version>\\API.x64\\my_plugin\\main.py``, and run
  it from cadwork's API menu.

cadwork ships no ``python.exe``; pycadwork is made importable by landing it in
cadwork's embedded ``site-packages`` once — a directory junction for the package
plus ``pip install --target`` for native deps like ``rtree``. The pycadwork repo
automates both in ``scripts\\Install-PycadworkRuntime.ps1``. After that, this
file simply ``import pycadwork`` — there is **no** ``sys.path`` manipulation.
"""

try:
    import pycadwork  # noqa: F401  (import-only check that the runtime install is in place)
    from pycadwork import Document
except ImportError as exc:  # pragma: no cover - guidance for an un-provisioned interpreter
    raise ImportError(
        "pycadwork is not importable from cadwork's interpreter. From the "
        "pycadwork checkout, run scripts\\Install-PycadworkRuntime.ps1 to link "
        "the package and install its dependencies into cadwork's site-packages."
    ) from exc


def main() -> None:
    """Plugin body — replace with real work against the live model."""
    doc = Document()
    elements = doc.elements()
    print(f"pycadwork {pycadwork.__file__}")
    print(f"model has {len(elements)} identifiable element(s)")


if __name__ == "__main__":
    main()

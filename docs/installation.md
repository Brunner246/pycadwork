# Installation

`pycadwork` targets **Python 3.14+** and is managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync                 # install the library + dev dependencies
uv sync --extra cadwork # include the cwapi3d runtime dependency explicitly
```

Or with pip:

```bash
pip install -e .
```

> **Note** — `cwapi3d` only does real work inside a running cadwork 3D process.
> Outside cadwork (CI, local dev, tests) the library still imports and runs; you
> just swap the adapter for the in-memory fake (see [Testing](testing.md)).

## Using pycadwork inside cadwork: development vs runtime

cadwork ships **no standalone `python.exe`** — its Python is an embedded
interpreter (`python3xx.dll`) loaded *inside the running cadwork process*. So you
never "activate" anything and never run `pip` against cadwork's Python; the only
thing you act on is the interpreter's `site-packages` directory (e.g.
`exe_2026\pclib.x64\python314\site-packages`), which it loads at startup.

There are two environments, both fed from this one checkout:

| Method                    | Environment                      | Gets deps?                  | Live edits? |
|---------------------------|----------------------------------|-----------------------------|-------------|
| `uv sync --extra cadwork` | development (IDE, types, tests)  | yes (`rtree`, `cwapi3d`)     | yes         |
| junction / `.pth`         | cadwork runtime                  | no — package only           | yes         |
| `pip install --target`    | cadwork runtime                  | yes (native `rtree`)        | n/a         |

**Development** — autocompletion, type-checking, and the test suite — is the `uv`
venv from the top of this page: `uv sync --extra cadwork` resolves
`pycadwork`, `rtree`, and the `cwapi3d` type surface for your IDE. Nothing
cadwork-specific is needed here.

**Runtime** means landing files in cadwork's `site-packages`. Two pieces:

### 1. The package — a directory junction (no copy, live edits)

Link the repo's `src\pycadwork` into cadwork's `site-packages` so the runtime
uses the *same checkout your IDE points at* — edits take effect immediately:

```
<site-packages>\pycadwork  -->  <repo>\src\pycadwork
```

A helper does this (PowerShell, **no admin needed** — a junction isn't a
privileged symlink). Both ends are parameters with sensible defaults:

```powershell
# defaults: this repo's src\pycadwork  ->  exe_2026 / python314 site-packages
.\scripts\Install-PycadworkJunction.ps1

# point both ends yourself: a specific checkout into a specific cadwork version
.\scripts\Install-PycadworkJunction.ps1 `
    -Source "C:\dev\pycadwork\src\pycadwork" `
    -Target "D:\cadwork.dir\exe_2027\pclib.x64\python314\site-packages\pycadwork"

.\scripts\Install-PycadworkJunction.ps1 -Force    # replace an existing link
.\scripts\Install-PycadworkJunction.ps1 -Remove   # unlink (leaves -Source intact)
```

It is the equivalent of the classic `cmd` one-liner
`mklink /J "<site-packages>\pycadwork" "<repo>\src\pycadwork"`; the script
refuses to clobber a real folder and is idempotent. (A one-line `.pth` file in
`site-packages` pointing at `src` is an equivalent alternative.)

### 2. Native dependencies — `pip install --target`

The junction exposes only the `pycadwork` package. `cwapi3d` is already present
inside cadwork, and the pure-Python core imports with nothing else — the spatial
index and connectivity helpers additionally need `rtree` (libspatialindex),
imported lazily, so `from pycadwork import …` works without it; only building an
index requires it. Since there is no cadwork `python.exe` to `pip` with, install
`rtree` **from your dev Python** — which shares cadwork's `cp314` / `win_amd64`
wheel tag, so the native wheel matches — straight into cadwork's `site-packages`:

```powershell
uv pip install --target "D:\cadwork.dir\exe_2026\pclib.x64\python314\site-packages" rtree
```

`Install-PycadworkRuntime.ps1` does **both** steps (junction + `--target` deps)
in one call:

```powershell
.\scripts\Install-PycadworkRuntime.ps1            # junction + rtree into cadwork's site-packages
.\scripts\Install-PycadworkRuntime.ps1 -Uninstall # remove both
```

Verify from cadwork's own Python console (the only interpreter that can import it):

```python
import pycadwork

print(pycadwork.__file__)  # -> ...\src\pycadwork\__init__.py
```

> **Why not `sys.path` manipulation?** Prepending a dev venv's `site-packages` in
> each plugin hardcodes a layout, repeats boilerplate across every plugin, and
> can load an `rtree` built for the wrong interpreter. Installing once via the
> junction + `--target` lets every plugin simply `import pycadwork` with no path
> code — see [`templates/my-plugin/main.py`](../templates/my-plugin/main.py).

### Developing a plugin as its own `uv` project

The two environments above also describe how to build a *separate* plugin
project: develop it in your own `uv` project (for autocompletion, types, and
tests), then run it inside cadwork (where the live model is). In your plugin's
`pyproject.toml` you don't use `uv sync --extra cadwork` — that extra is
pycadwork's own and only applies inside this repo. Instead you depend on
pycadwork and request the extra through the dependency spec, pointing uv at a
checkout since pycadwork isn't on PyPI yet:

```toml
[project]
requires-python = ">=3.14"
dependencies = ["pycadwork[cadwork]"]   # [cadwork] adds cwapi3d for autocomplete

[tool.uv.sources]
pycadwork = { path = "../pycadwork", editable = true }   # or a git = { ... } source
```

then a plain `uv sync`. A ready-to-copy starter — `pyproject.toml`, an
`import`-only `main.py`, and a walkthrough — lives in
[`templates/my-plugin/`](../templates/my-plugin/). Copy that folder out of the repo,
adjust the `pycadwork` source path, and start editing.

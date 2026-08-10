# my-plugin — a pycadwork plugin starter

A minimal, copy-me starter for building a cadwork plugin on top of
[pycadwork](https://github.com/Brunner246/pycadwork). Copy this whole folder out
of the pycadwork repo to wherever you keep your plugins, rename it, and start
editing `main.py`.

It exists to make one workflow concrete: **develop in your own `uv` project (for
autocompletion, types, and tests), run inside cadwork (where the live model
is).** Those are two different environments fed from the same pycadwork checkout.

## 1. Set up the dev environment

Prerequisites: [uv](https://docs.astral.sh/uv/) and a pycadwork checkout.

By default `pyproject.toml` expects pycadwork to sit *beside* this project:

```
<parent>/
  pycadwork/      <- your pycadwork checkout
  my-plugin/      <- this project
```

If your layout differs, edit the `pycadwork` entry under `[tool.uv.sources]` in
`pyproject.toml` (point `path` at your checkout, or switch to the `git` source).
Then:

```bash
uv sync
```

That provisions a venv with `pycadwork` (editable), its `rtree` dependency, and
`cwapi3d` (the `[cadwork]` extra) so your IDE resolves every symbol. Note: this
is plain `uv sync` — **not** `uv sync --extra cadwork`. `--extra cadwork` is
pycadwork's *own* extra and only applies inside the pycadwork repo; here the
extra is requested through the dependency spec `pycadwork[cadwork]`.

> Don't call `cwapi3d` directly? Drop the extra — depend on plain `"pycadwork"`.
> You still get full autocomplete for the pycadwork API and `rtree`.

## 2. Develop

- IDE autocompletion / type-checking work immediately against the venv.
- Put pure, testable logic in your own modules and run `uv run pytest`.
- You do **not** run `main()` outside cadwork — it queries the live model, which
  only exists in a running cadwork process. Keep `main()` a thin shell over your
  pure logic.

## 3. Run inside cadwork

cadwork ships no `python.exe`, so pycadwork is made importable by landing it in
cadwork's embedded `site-packages` once. From your **pycadwork checkout**:

```powershell
.\scripts\Install-PycadworkRuntime.ps1
```

(That creates the package junction and installs `rtree` via `pip --target` — see
the pycadwork README, "Using pycadwork inside cadwork: development vs runtime".)

Then copy `main.py` into your cadwork userprofile API folder, e.g.:

```
<userprofile>\<version>\API.x64\my_plugin\main.py
```

and run it from cadwork's API menu. It just `import pycadwork` — no `sys.path`
manipulation.

## Why two environments?

Your project directory is where you *develop* (edit, autocomplete, test). cadwork's
`site-packages` is where pycadwork *runs*. The dev venv never makes the plugin
runnable inside cadwork, and the cadwork install never gives your IDE
autocompletion — you want both, so you set up both, off one pycadwork checkout.

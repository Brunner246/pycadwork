# The `cadwork` terminal wrapper

cadwork's `ci_start.exe` takes an uncommon slash-based command line
(`/INSTALL /SILENT`, `/SET_LICENCE="…"`, `file.2d /P A`). The `pycadwork.terminal`
package wraps it in a state-of-the-art CLI — `cadwork <verb> [--options]` — that
parses modern arguments, translates them into the exact `/SLASH` tokens, and
launches cadwork. A global `--dry-run` prints the command line instead of running
it.

```powershell
cadwork open house.3d --plugin ExportBTL --exe exe_2026
# runs:  ci_start.exe "house.3d" /EXE=exe_2026 /PLUGIN=ExportBTL

cadwork install --silent --desktop-shortcut --dry-run
# prints: ci_start.exe /INSTALL /SILENT /SHORTCUT_ON_DESKTOP
```

> **Where it runs** — this wrapper *launches* cadwork, so it runs on a normal
> **host** Python (PowerShell / cmd), **not** inside cadwork's embedded
> interpreter. It imports no `cwapi3d` and is independent of the cadwork adapter
> seam.

## Make `cadwork` available everywhere

The package declares a console entry point (`[project.scripts]` in
`pyproject.toml`):

```toml
[project.scripts]
cadwork = "pycadwork.terminal.cli:main"
```

Installing the package creates a `cadwork.exe` launcher. To call `cadwork` from
**any** PowerShell or cmd window, that launcher's folder must be on your `PATH`.
Pick one of the following.

### Option A — `uv tool install` (recommended)

[`uv tool`](https://docs.astral.sh/uv/guides/tools/) installs a CLI into its own
isolated environment and puts the launcher on `PATH` for you:

```powershell
# from a clone of this repo
uv tool install .

# …or, once published, straight from PyPI
uv tool install pycadwork

# first time only: ensure uv's tool-bin dir is on PATH, then reopen the shell
uv tool update-shell
```

`uv tool install` pulls the runtime dependencies (`cwapi3d`, `rtree`) into the
tool's own environment, so `cadwork` works standalone — you do **not** need
cadwork running or a project venv activated.

Upgrade or remove later with:

```powershell
uv tool upgrade pycadwork
uv tool uninstall pycadwork
```

### Option B — `pipx`

```powershell
pipx install .            # from a repo clone
pipx install pycadwork    # from PyPI
pipx ensurepath           # add pipx's bin dir to PATH (reopen the shell after)
```

### Option C — a plain `pip` virtual environment

```powershell
py -m venv C:\tools\cadwork-cli
C:\tools\cadwork-cli\Scripts\pip install pycadwork    # or: pip install .
```

This puts `cadwork.exe` in `C:\tools\cadwork-cli\Scripts`. Either activate that
venv, or add its `Scripts` folder to `PATH` (see below) to call `cadwork` from
anywhere.

### Option D — inside this repo, no install

For development you don't need to install anything — `uv run` resolves the entry
point from the checkout (this form works only inside the repo):

```powershell
uv run cadwork open house.3d --dry-run
```

### Verify it's on PATH

```powershell
cadwork --help
Get-Command cadwork        # PowerShell: shows the resolved cadwork.exe path
```

```cmd
cadwork --help
where cadwork              :: cmd: shows the resolved cadwork.exe path
```

### Adding a folder to PATH manually

If you used Option C (or `uv tool` / `pipx` didn't update your shell), add the
launcher's folder to `PATH`:

```powershell
# PowerShell — persist for the current user (reopen the shell afterwards)
[Environment]::SetEnvironmentVariable(
    "Path",
    [Environment]::GetEnvironmentVariable("Path", "User") + ";C:\tools\cadwork-cli\Scripts",
    "User")
```

```cmd
:: cmd — persist for the current user (reopen the shell afterwards)
setx PATH "%PATH%;C:\tools\cadwork-cli\Scripts"
```

## Pointing the wrapper at `ci_start.exe`

Unless you use `--dry-run`, the wrapper needs to find `ci_start.exe`. It resolves
in this order:

1. `--ci-start PATH` — an explicit path, wins over everything.
2. `CADWORK_CI_START` — an environment variable naming the executable.
3. `ci_start` on your `PATH`.
4. **The registry** — cadwork's own `CADWORK.DIR` value under
   `HKEY_CURRENT_USER\Software\cadwork Informatik\ENV`; `ci_start.exe` lives in
   that folder. This means a normally-installed cadwork is found automatically,
   with nothing to configure.
5. Common install locations (`C:\cadwork.dir\exe_*\ci_start.exe`,
   `C:\Program Files\cadwork.dir\exe_*\ci_start.exe`) — newest `exe_*` first.

If none match, the command exits with a clear "could not locate ci_start.exe"
error (exit code `2`).

> On a standard cadwork install you usually need none of the above — step 4 finds
> `ci_start.exe` from the registry. Use `--ci-start` / `CADWORK_CI_START` only to
> override which install the wrapper drives.

The same registry block holds cadwork's other configured paths (EXE, userprofile,
catalog, projects folders). You can read any of them programmatically:

```python
from pycadwork.terminal import read_env_value

read_env_value("CADWORK.DIR")   # 'D:\\cadwork.dir'
read_env_value("CADWORK_EXE")   # 'D:\\cadwork.dir\\EXE_2026'
read_env_value("CADWORK_USP")   # the userprofile folder, etc.
```

Set the environment variable once so every window finds cadwork:

```powershell
# PowerShell — persist for the current user (reopen the shell afterwards)
setx CADWORK_CI_START "C:\cadwork.dir\exe_2026\ci_start.exe"

# …or just for the current session
$env:CADWORK_CI_START = "C:\cadwork.dir\exe_2026\ci_start.exe"
```

```cmd
:: cmd — persist for the current user (reopen the shell afterwards)
setx CADWORK_CI_START "C:\cadwork.dir\exe_2026\ci_start.exe"

:: …or just for the current session
set CADWORK_CI_START=C:\cadwork.dir\exe_2026\ci_start.exe
```

…or pass it per-call: `cadwork update all --ci-start "C:\cadwork.dir\exe_2026\ci_start.exe"`.

## Commands

Every verb accepts the global options `--ci-start PATH`, `--log-file PATH`
(→ `/LogFile`), and `--dry-run`. Run `cadwork <verb> --help` for the full option
list.

| Command | Purpose | Example |
|---------|---------|---------|
| `open FILE` | Open a model, optionally run a plugin | `cadwork open house.3d --plugin ExportBTL --exe exe_2026` |
| `install` | Install cadwork on this PC | `cadwork install --silent --desktop-shortcut --user holz` |
| `uninstall` | Uninstall cadwork | `cadwork uninstall --silent --purge --close` |
| `licence get` | Print the default licence | `cadwork licence get` |
| `licence set VALUE` | Set the default licence | `cadwork licence set "WEB Licence:00.000.0#1;PASSWORD"` |
| `licence no-network` | Use the USB-stick licence | `cadwork licence no-network` |
| `update [2d\|all\|all-force]` | Live-update modules (default `all`) | `cadwork update all --silent --maximized` |
| `print FILE` | Print a `.2d` (frames) or `.txt` file | `cadwork print plan.2d --plotter A` |

`open` options map to `/EXE` `/PLUGIN` `/RUNPROGRAM` `/NO-GUI` `/USP` `/CATDIR`
`/WORKDIR`:

| CLI option | cadwork flag | Notes |
|------------|--------------|-------|
| `--plugin NAME` | `/PLUGIN` | Plugin folder name in `API.x64` |
| `--run-program PATH` | `/RUNPROGRAM` | Full path to a `.py` or `.dll` anywhere (not only `API.x64`) |
| `--no-gui` | `/NO-GUI` | Headless; requires `--plugin` or `--run-program` |

```powershell
cadwork open .\Downloads\test_elements_walls.3d --exe D:\cadwork.dir\exe_2026 `
    --run-program C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py
# runs: ci_start.exe ".\Downloads\test_elements_walls.3d" /EXE=D:\cadwork.dir\exe_2026 /RUNPROGRAM="C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py"

# headless automation (no GUI window)
cadwork open house.3d --run-program C:\my_plugins\export.py --no-gui
# runs: ci_start.exe "house.3d" /RUNPROGRAM="C:\my_plugins\export.py" /NO-GUI

cadwork open house.3d --plugin MyExport --no-gui
# runs: ci_start.exe "house.3d" /PLUGIN=MyExport /NO-GUI
```

`print` uses
`--plotter` (→ `/P`) or `--laser` (→ `/L`), where frames are `A` (all) or a spec
like `1-2;5;7`, and `--laser PDF` prints to the PDF driver.

## Shell quoting

Quote any value that contains a space, and — **in PowerShell** — any value with a
`;` (PowerShell treats `;` as a statement separator):

```powershell
# PowerShell
cadwork print plan.2d --plotter "1-2;5;7"
cadwork licence set "WEB Licence:00.000.0#1;PASSWORD"
cadwork open "C:\My Projects\house.3d" --workdir "C:\My Documents"
```

```cmd
:: cmd — spaces still need quotes; ; is fine unquoted
cadwork print plan.2d --plotter 1-2;5;7
cadwork licence set "WEB Licence:00.000.0#1;PASSWORD"
cadwork open "C:\My Projects\house.3d" --workdir "C:\My Documents"
```

Reach for `--dry-run` whenever you're unsure how a line will be translated — it
prints the exact `ci_start.exe` command without executing it.

## Output

A real launch echoes the resolved command line to **stderr** (so **stdout** stays
clean for piping) and reports a non-zero exit code; on success it is otherwise
quiet — `ci_start.exe` hands off to cadwork and returns immediately:

```
launching: D:\cadwork.dir\ci_start.exe "C:\Users\...\house.3d"
```

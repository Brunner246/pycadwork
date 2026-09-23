# The `cadwork` terminal wrapper

`pycadwork.terminal` is a `cadwork <verb> [--options]` CLI. `open` starts
`3d.exe` directly (PATH + `CADWORK_EXE` / `CADWORK_LIB` pinned to that
version, then waits until 3d exits). Install / uninstall / licence / update /
print still go through cadwork's Filemanager (`ci_start.exe`) and its
uncommon slash-based command line (`/INSTALL /SILENT`, `/SET_LICENCE="…"`,
`file.2d /P A`). A global `--dry-run` prints the command line instead of
running it.

```powershell
cadwork open house.3d --plugin ExportBTL --exe exe_2026
# runs:  …\exe_2026\3d.x64\3d.exe "house.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg /PLUGIN=ExportBTL

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

## Pointing `open` at `3d.exe`

`cadwork open` locates `3d.x64\3d.exe` in this order:

1. `--exe DIR` — an existing version folder (`D:\cadwork.dir\exe_2026`) or a
   folder *name* (`exe_2026`) resolved under the registry `CADWORK.DIR`.
2. **The registry** — `CADWORK_EXE` under
   `HKEY_CURRENT_USER\Software\cadwork Informatik\ENV`
   (`<CADWORK_EXE>\3d.x64\3d.exe`).
3. Common install locations (`C:\cadwork.dir\exe_*\3d.x64\3d.exe`,
   `C:\Program Files\cadwork.dir\exe_*\3d.x64\3d.exe`,
   `D:\cadwork.dir\exe_*\3d.x64\3d.exe`) — newest `exe_*` first.

If none match, the command exits with a clear "could not locate 3d.exe" error
(exit code `2`). Prefer a full `--exe` path when several versions are
installed — that is how a mixed-version machine avoids loading the wrong
`python314.dll` / Qt.

The child process gets this version's folders prepended onto `PATH`, plus
`CADWORK_EXE` / `CADWORK_LIB`. When `pclib.x64\tcl\lib` exists it also sets
`TCLLIBPATH` to that folder and `TCL_LIBRARY` / `TK_LIBRARY` to the `tcl8.6`
/ `tk8.6` children that contain `init.tcl` / `tk.tcl` (legacy `TCL8.2` is
used only if 8.6 is absent). That overlay is required because the process
is `3d.exe`: Tcl's default search is relative to the executable
(`exe_YYYY\lib\tcl8.6`, …) and never sees `pclib.x64\tcl\lib`, which is
where cadwork ships the scripts tkinter / IDLE need.
`open` **waits** until `3d.exe` exits. Other files can be opened while 3d is
running; only `--usp` errors, and only when the same version is already running
with a different userprofile (a live instance keeps the profile it loaded).

## Pointing Filemanager verbs at `ci_start.exe`

`install` / `uninstall` / `licence` / `update` / `print` still need
`ci_start.exe` (unless you use `--dry-run`). Resolution order:

1. `--ci-start PATH` — an explicit path, wins over everything.
2. `CADWORK_CI_START` — an environment variable naming the executable.
3. `ci_start` on your `PATH`.
4. **The registry** — cadwork's own `CADWORK.DIR` value; `ci_start.exe` lives in
   that folder.
5. Common install locations (`C:\cadwork.dir\exe_*\ci_start.exe`,
   `C:\Program Files\cadwork.dir\exe_*\ci_start.exe`) — newest `exe_*` first.

If none match, the command exits with a clear "could not locate ci_start.exe"
error (exit code `2`).

> On a standard cadwork install you usually need none of the above — the
> registry finds both `3d.exe` and `ci_start.exe`. Use `--exe` / `--ci-start`
> only to override which install the wrapper drives.

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

Every verb accepts `--log-file PATH` (→ `/LogFile`) and `--dry-run`. Filemanager
verbs also accept `--ci-start PATH`. Run `cadwork <verb> --help` for the full
option list.

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

`open` always sends `/Console` and `/AlwaysIgnoreMultiOpenProtectDlg`, then
maps the rest:

| CLI option | cadwork flag | Notes |
|------------|--------------|-------|
| `--exe DIR` | *(selects the binary)* | Version folder. Prefer a full path (`D:\cadwork.dir\exe_2026`). Not a `/EXE=` token — that is which `3d.exe` to start. |
| `--plugin NAME` | `/PLUGIN` | Plugin folder name in `API.x64` |
| `--run-program PATH` | `/RUNPROGRAM` | Full path to a `.py` or `.dll` anywhere (not only `API.x64`) |
| `--no-gui` | `/NO-GUI` | Headless; requires `--plugin` or `--run-program` |
| `--usp DIR` | `/USP` | Userprofile **root** (not the `3d` subfolder). Forward slashes are accepted; cadwork is sent `D:\…`. 3d reads `CADWORK_USP` from **HKCU**, not from `/USP` or the process environment. The wrapper pins `CADWORK_USP` for the 3d session and restores it when 3d exits. Errors only if a `3d.exe` of the **same version** (same `exe_YYYY` tree) is already running and the requested profile differs from the current `CADWORK_USP` — a running 3d keeps the profile it loaded. Other versions are independent, and `open` without `--usp` always launches. |
| `--catdir DIR` | `/CATDIR` | Catalog folder (`CADWORK_CAT` on the launched process). Forward slashes are normalized the same way as `--usp`. |
| `--workdir DIR` | `/WORKDIR` | Projects folder. |

```powershell
cadwork open .\Downloads\test_elements_walls.3d --exe D:\cadwork.dir\exe_2026 `
    --run-program C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py
# runs: "D:\cadwork.dir\exe_2026\3d.x64\3d.exe" ".\Downloads\test_elements_walls.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg /RUNPROGRAM="C:\Users\MichaelBrunner\Downloads\export_elements_jsonl.py"

# headless automation (no GUI window); the CLI waits until 3d exits
cadwork open house.3d --run-program C:\my_plugins\export.py --no-gui
# runs: …\3d.exe "house.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg /RUNPROGRAM="C:\my_plugins\export.py" /NO-GUI

cadwork open house.3d --plugin MyExport --no-gui
# runs: …\3d.exe "house.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg /PLUGIN=MyExport /NO-GUI

# different userprofile than the registry default (errors if exe_2026's 3d.exe is
# already running with another profile; an exe_2027 instance does not block)
cadwork open "C:\Users\MichaelBrunner\Downloads\test_elements_walls.3d" `
    --exe D:\cadwork.dir\exe_2026 --usp D:/cadwork/userprofil_2026_charts
# runs: "D:\cadwork.dir\exe_2026\3d.x64\3d.exe" "C:\Users\...\test_elements_walls.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg /USP="D:\cadwork\userprofil_2026_charts"
# pins HKCU CADWORK_USP for that 3d session (restored when 3d exits)
```

`CADWORK_USP` is a single HKCU value shared by all versions. Launching another
version with `--usp` while one is running rewrites it for the new session only —
the running instance already loaded its profile. If `--usp` sessions overlap, each
restores the value it found when that session's 3d exits, so the last one to exit decides what stays.

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
prints the command without executing it (`3d.exe` for `open`, `ci_start.exe`
for Filemanager verbs). A real launch uses that same quoting (not Windows
argv/`list2cmdline`).

`--usp` is proven by the opt-in cadwork IT
`tests/terminal/test_cadwork_usp.py` (set `PYCADWORK_CADWORK_IT=1`): a
`--run-program` probe calls `utility_controller.get_3d_userprofil_path()` inside
3d and asserts it is the requested folder, not the registry default.

## Output

A real launch echoes the resolved command line to **stderr** (so **stdout** stays
clean for piping) and reports a non-zero exit code; on success it is otherwise
quiet. `open` waits until `3d.exe` exits (then restores any `--usp` registry
pin). Filemanager verbs still return when `ci_start.exe` does:

```
launching: "D:\cadwork.dir\exe_2026\3d.x64\3d.exe" "C:\Users\...\house.3d" /Console /AlwaysIgnoreMultiOpenProtectDlg
```

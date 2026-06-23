#Requires -Version 5.1
<#
.SYNOPSIS
    Make pycadwork importable from inside cadwork in one call: link the package
    source into cadwork's site-packages and install its native dependencies.

.DESCRIPTION
    cadwork ships NO standalone python.exe — its Python is an embedded
    interpreter (python3xx.dll) loaded inside the running cadwork process. You
    therefore cannot run `pip` against cadwork's Python; the only thing you can
    act on is the embedded interpreter's `site-packages` directory, which it
    loads at startup. This script makes pycadwork available there with two steps,
    neither of which invokes a cadwork interpreter:

      1. Package  — a directory junction  <site-packages>\pycadwork -> <repo>\src\pycadwork
                    (delegated to Install-PycadworkJunction.ps1). No copy; edits
                    in the repo take effect immediately, and runtime uses the
                    same checkout your IDE points at.

      2. Deps     — `rtree` (libspatialindex) installed with `pip install
                    --target <site-packages>` from a HOST interpreter that shares
                    cadwork's wheel tag (cp314 / win_amd64). The default host is
                    this repo's `uv` environment, whose Python is 3.14 — the same
                    tag as cadwork's `python314` — so the native wheel matches.

    After this runs, plugins inside cadwork simply `import pycadwork` (and use the
    spatial index) with NO sys.path manipulation.

.PARAMETER SitePackages
    cadwork's embedded-interpreter site-packages directory (the parent of the
    `pycadwork` junction). Must already exist. Defaults to the exe_2026 /
    python314 location, matching Install-PycadworkJunction.ps1.

.PARAMETER Source
    The pycadwork package directory to link to (passed through to the junction
    script). Defaults to this repo's `src\pycadwork`, resolved from the script.

.PARAMETER HostPython
    Path to a host python.exe used to install the native deps. When omitted, the
    script uses `uv pip install` from the repo root (no pip needed in the venv).
    Pass an explicit interpreter to use `<HostPython> -m pip` instead — it MUST
    share cadwork's tag (e.g. CPython 3.14, win_amd64, non-free-threaded).

.PARAMETER Force
    Replace an existing junction at the target (passed through to the junction
    script). Does not affect the deps step (pip handles its own overwrite).

.PARAMETER Uninstall
    Remove the junction and the --target-installed `rtree` from site-packages.

.EXAMPLE
    .\scripts\Install-PycadworkRuntime.ps1
    Junction + rtree into cadwork's default site-packages.

.EXAMPLE
    .\scripts\Install-PycadworkRuntime.ps1 `
        -SitePackages "D:\cadwork.dir\exe_2027\pclib.x64\python314\site-packages"
    Target a specific cadwork version.

.EXAMPLE
    .\scripts\Install-PycadworkRuntime.ps1 -Uninstall
    Remove both the junction and the installed deps.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$SitePackages = "D:\cadwork.dir\exe_2026\pclib.x64\python314\site-packages",
    [string]$Source = (Join-Path $PSScriptRoot "..\src\pycadwork"),
    [string]$HostPython,
    [switch]$Force,
    [switch]$Uninstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$junctionScript = Join-Path $PSScriptRoot "Install-PycadworkJunction.ps1"
$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$packageJunction = Join-Path $SitePackages "pycadwork"

# Third-party packages this script installs into cadwork's site-packages. The
# core package imports with none of these; only the spatial index needs rtree.
$deps = @("rtree")
# Top-level import directories a `--target` install of $deps drops into
# site-packages — what we check for / remove (rtree ships its own dist-info too,
# but removing the package dir is enough to make it un-importable).
$depDirs = @("rtree")

function Resolve-SitePackages {
    if (-not (Test-Path -LiteralPath $SitePackages -PathType Container)) {
        throw "site-packages not found: '$SitePackages'. Check the cadwork version / Python folder (exe_YYYY, pythonNNN) and pass -SitePackages."
    }
    return (Resolve-Path -LiteralPath $SitePackages).Path
}

# ---- uninstall mode ----

if ($Uninstall) {
    $SitePackages = Resolve-SitePackages

    & $junctionScript -Target $packageJunction -Remove

    foreach ($dir in $depDirs) {
        $path = Join-Path $SitePackages $dir
        if (Test-Path -LiteralPath $path) {
            if ($PSCmdlet.ShouldProcess($path, "Remove installed dependency")) {
                Remove-Item -LiteralPath $path -Recurse -Force
                Write-Host "Removed dependency: $path" -ForegroundColor Green
            }
        }
    }
    # Sweep matching dist-info/egg-info metadata for the removed deps.
    foreach ($dep in $deps) {
        Get-ChildItem -LiteralPath $SitePackages -Directory -Filter "$dep-*.dist-info" -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($PSCmdlet.ShouldProcess($_.FullName, "Remove dependency metadata")) {
                    Remove-Item -LiteralPath $_.FullName -Recurse -Force
                }
            }
    }
    Write-Host "pycadwork runtime uninstalled from: $SitePackages" -ForegroundColor Green
    return
}

# ---- install mode ----

$SitePackages = Resolve-SitePackages

# Step 1 — the package junction (delegated; it does its own validation).
Write-Host "[1/2] Linking pycadwork source into cadwork's site-packages..." -ForegroundColor Cyan
$junctionArgs = @{ Source = $Source; Target = $packageJunction }
if ($Force) { $junctionArgs.Force = $true }
& $junctionScript @junctionArgs

# Step 2 — native deps via a host interpreter that matches cadwork's wheel tag.
Write-Host "[2/2] Installing native dependencies ($($deps -join ', ')) into site-packages..." -ForegroundColor Cyan

if ($HostPython) {
    if (-not (Test-Path -LiteralPath $HostPython -PathType Leaf)) {
        throw "HostPython not found: '$HostPython'."
    }
    $installAction = "& '$HostPython' -m pip install --target '$SitePackages' $($deps -join ' ')"
    if ($PSCmdlet.ShouldProcess($SitePackages, $installAction)) {
        & $HostPython -m pip install --target $SitePackages @deps
        if ($LASTEXITCODE -ne 0) { throw "pip install --target failed (exit $LASTEXITCODE)." }
    }
}
else {
    # Default: uv from the repo root. `uv pip install` targets the project's
    # Python (3.14) and needs no pip inside the venv.
    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if (-not $uv) {
        throw "uv not found on PATH. Install uv, or pass -HostPython pointing at a CPython 3.14 (win_amd64) interpreter."
    }
    $installAction = "uv pip install --target '$SitePackages' $($deps -join ' ')  (cwd: $repoRoot)"
    if ($PSCmdlet.ShouldProcess($SitePackages, $installAction)) {
        Push-Location $repoRoot
        try {
            & uv pip install --target $SitePackages @deps
            if ($LASTEXITCODE -ne 0) { throw "uv pip install --target failed (exit $LASTEXITCODE)." }
        }
        finally {
            Pop-Location
        }
    }
}

# ---- verify by path (no cadwork interpreter exists to import with) ----

Write-Host ""
$okPackage = Test-Path -LiteralPath $packageJunction
$okDeps = $depDirs | ForEach-Object { Test-Path -LiteralPath (Join-Path $SitePackages $_) }
if ($okPackage -and ($okDeps -notcontains $false)) {
    Write-Host "pycadwork runtime ready in: $SitePackages" -ForegroundColor Green
    Write-Host "    pycadwork -> $packageJunction"
    Write-Host "    deps      -> $($deps -join ', ')"
    Write-Host ""
    Write-Host "Verify from cadwork's own Python console:  import pycadwork; print(pycadwork.__file__)"
}
else {
    Write-Host "Install completed but verification is incomplete:" -ForegroundColor Yellow
    Write-Host "    pycadwork junction present: $okPackage"
    Write-Host "    dependency dirs present:    $($okDeps -join ', ')"
}

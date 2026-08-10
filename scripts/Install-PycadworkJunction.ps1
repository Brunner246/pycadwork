#Requires -Version 5.1
<#
.SYNOPSIS
    Link a pycadwork source directory into cadwork's bundled Python site-packages.

.DESCRIPTION
    cadwork ships its own embedded CPython (e.g. exe_2026\pclib.x64\python314).
    To run pycadwork *from source* inside cadwork — so edits in the repo take
    effect immediately, with no copy or reinstall step — we expose the package
    directory to that interpreter via a directory junction:

        <Target>  -->  <Source>

    A junction (the same thing `mklink /J` creates) needs no administrator
    rights and survives reboots. Both ends are parameters: -Source is the
    package directory to link to, -Target is the junction path to create. Both
    default to a standard repo + cadwork layout, so you can run the script with
    no arguments — or override either end for a different checkout or cadwork
    version.

.PARAMETER Source
    The pycadwork package directory to link to (the junction's target on disk).
    Defaults to this repo's `src\pycadwork`, resolved relative to the script.

.PARAMETER Target
    The full junction path to create inside cadwork's site-packages. Its parent
    (the site-packages directory) must already exist. Defaults to the exe_2026 /
    python314 location with a `pycadwork` leaf.

.PARAMETER Force
    Replace an existing entry at -Target (junction or folder). Without this, an
    existing entry is left untouched.

.PARAMETER Remove
    Remove the junction at -Target instead of creating it. Only removes the link
    itself; the -Source files are never touched.

.EXAMPLE
    .\scripts\Install-PycadworkJunction.ps1
    Create the junction using the default source and target.

.EXAMPLE
    .\scripts\Install-PycadworkJunction.ps1 `
        -Source "C:\dev\pycadwork\src\pycadwork" `
        -Target "D:\cadwork.dir\exe_2027\pclib.x64\python314\site-packages\pycadwork"
    Link a specific checkout into a specific cadwork version.

.EXAMPLE
    .\scripts\Install-PycadworkJunction.ps1 -Force
    Recreate the junction, replacing whatever is at the target now.

.EXAMPLE
    .\scripts\Install-PycadworkJunction.ps1 -Remove
    Unlink (leaves the source intact).
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [string]$Source = (Join-Path $PSScriptRoot "..\src\pycadwork"),
    [string]$Target = "D:\cadwork.dir\exe_2026\pclib.x64\python314\site-packages\pycadwork",
    [switch]$Force,
    [switch]$Remove
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Test-IsJunction {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) { return $false }
    $item = Get-Item -LiteralPath $Path -Force
    return [bool]($item.Attributes -band [IO.FileAttributes]::ReparsePoint)
}

function Remove-Junction {
    param([string]$Path)
    # rmdir on a junction removes only the link, never the target's contents.
    & cmd.exe /c rmdir "$Path" | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Failed to remove the junction at '$Path'." }
}

# ---- remove mode ----

if ($Remove) {
    if (-not (Test-Path -LiteralPath $Target)) {
        Write-Host "Nothing to remove: '$Target' does not exist." -ForegroundColor Yellow
        return
    }
    if (-not (Test-IsJunction $Target)) {
        throw "'$Target' is not a junction (it looks like a real folder). Refusing to delete it; inspect it manually."
    }
    if ($PSCmdlet.ShouldProcess($Target, "Remove junction")) {
        Remove-Junction $Target
        Write-Host "Removed junction: $Target" -ForegroundColor Green
    }
    return
}

# ---- create / replace ----

# Resolve and validate the source package directory.
try {
    $Source = (Resolve-Path -LiteralPath $Source).Path
}
catch {
    throw "Source not found: '$Source'. Pass -Source pointing at a pycadwork package directory."
}
if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
    throw "Source is not a directory: '$Source'."
}

# The junction's parent (cadwork's site-packages) must already exist.
# [IO.Path]::GetDirectoryName, not Split-Path: -LiteralPath is incompatible with
# -Parent (different parameter sets), and -Path would glob bracketed paths.
$targetParent = [System.IO.Path]::GetDirectoryName($Target)
if (-not (Test-Path -LiteralPath $targetParent -PathType Container)) {
    throw "Target parent not found: '$targetParent'. Check the cadwork version / Python folder (exe_YYYY, pythonNNN) and pass the correct path via -Target."
}

if (Test-Path -LiteralPath $Target) {
    $isJunction = Test-IsJunction $Target
    if (-not $Force) {
        $kind = if ($isJunction) { "junction" } else { "real folder" }
        Write-Host "'$Target' already exists ($kind). Use -Force to replace it." -ForegroundColor Yellow
        return
    }
    if (-not $isJunction) {
        throw "'$Target' is a real folder, not a junction. Refusing to overwrite it with -Force; move or delete it manually first."
    }
    if ($PSCmdlet.ShouldProcess($Target, "Remove existing junction before recreating")) {
        Remove-Junction $Target
    }
}

if ($PSCmdlet.ShouldProcess($Target, "Create junction -> $Source")) {
    New-Item -ItemType Junction -Path $Target -Target $Source | Out-Null
    Write-Host "Linked pycadwork source into cadwork's site-packages:" -ForegroundColor Green
    Write-Host "    $Target" -ForegroundColor Green
    Write-Host " -> $Source" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify from cadwork's Python with:  import pycadwork; print(pycadwork.__file__)"
}

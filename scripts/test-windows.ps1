[CmdletBinding()]
param(
    [string]$MsysRoot = $(if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { "C:\msys64" }),
    [string]$InstallRoot = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $InstallRoot) {
    $InstallRoot = Join-Path $repoRoot "build\install-x64"
}
$python = Join-Path $MsysRoot "mingw64\bin\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "MSYS2 Python was not found: $python"
}
if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot "python\_openshot.pyd") -PathType Leaf)) {
    throw "libopenshot Python bindings were not found under: $InstallRoot"
}

$env:PATH = "$(Join-Path $InstallRoot 'bin');$(Join-Path $MsysRoot 'mingw64\bin');$env:PATH"
$env:QT_QPA_PLATFORM = "offscreen"
& $python (Join-Path $PSScriptRoot "run_windows_tests.py") `
    --repo-root $repoRoot `
    --install-root $InstallRoot
if ($LASTEXITCODE -ne 0) {
    throw "Windows test suite failed with exit code $LASTEXITCODE"
}

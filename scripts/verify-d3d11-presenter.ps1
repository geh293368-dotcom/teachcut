[CmdletBinding()]
param(
    [string]$InputPath,
    [string]$MsysRoot = $(if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { "C:\msys64" }),
    [ValidateSet(5, 6)]
    [int]$QtMajor = 6,
    [int]$Frames = 60
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$installRoot = if ($QtMajor -eq 6) {
    Join-Path $repoRoot "build\install-x64-qt6"
} else {
    Join-Path $repoRoot "build\install-x64"
}
$python = Join-Path $MsysRoot "mingw64\bin\python.exe"
$ffmpeg = Join-Path $MsysRoot "mingw64\bin\ffmpeg.exe"

if (-not $InputPath) {
    $InputPath = Join-Path $repoRoot "build\benchmarks\synthetic-4k-h264.mp4"
}
$InputPath = [IO.Path]::GetFullPath($InputPath)

if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $InputPath) -Force | Out-Null
    & $ffmpeg -hide_banner -loglevel error -y `
        -f lavfi -i "testsrc2=size=3840x2160:rate=30" `
        -t 4 -c:v libx264 -preset veryfast -pix_fmt yuv420p -an $InputPath
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to generate the synthetic 4K verification clip."
    }
}

$env:PATH = "$installRoot\bin;$(Join-Path $MsysRoot 'mingw64\bin');$env:PATH"
$env:PYTHONPATH = "$installRoot\python;$repoRoot\src"
$env:OPENSHOT_INSTALL_ROOT = $installRoot
$env:OPENSHOT_QT_API = if ($QtMajor -eq 6) { "pyqt6" } else { "pyqt5" }
$env:QT_QPA_PLATFORM = "windows"

& $python (Join-Path $PSScriptRoot "verify_d3d11_presenter.py") $InputPath --frames $Frames
if ($LASTEXITCODE -ne 0) {
    throw "D3D11 presenter verification failed."
}

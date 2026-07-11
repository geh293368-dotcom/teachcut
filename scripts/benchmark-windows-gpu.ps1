[CmdletBinding()]
param(
    [string]$InputPath = "",
    [string]$MsysRoot = $(if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { "C:\msys64" }),
    [int]$DecodeFrames = 180,
    [int]$DecodeRepeats = 3,
    [int]$EncodeFrames = 90,
    [string]$ReportName = "rtx4090-4k-results",
    [switch]$SkipEncode
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$installRoot = Join-Path $repoRoot "build\install-x64"
$outputDir = Join-Path $repoRoot "build\benchmarks"
$python = Join-Path $MsysRoot "mingw64\bin\python.exe"
$ffmpeg = Join-Path $MsysRoot "mingw64\bin\ffmpeg.exe"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

if (-not $InputPath) {
    $InputPath = Join-Path $outputDir "synthetic-4k-h264.mp4"
    if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
        & $ffmpeg -hide_banner -y `
            -f lavfi -i "testsrc2=size=3840x2160:rate=30,noise=alls=6:allf=t+u" `
            -f lavfi -i "sine=frequency=1000:sample_rate=48000" `
            -t 6 `
            -c:v h264_nvenc -preset p4 -tune hq -rc vbr -cq 20 `
            -b:v 35M -maxrate 50M -bufsize 70M -pix_fmt yuv420p `
            -c:a aac -b:a 192k -shortest $InputPath
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to generate the synthetic 4K benchmark clip"
        }
    }
}
if (-not (Test-Path -LiteralPath $InputPath -PathType Leaf)) {
    throw "Benchmark input was not found: $InputPath"
}

$env:PATH = "$installRoot\bin;$(Join-Path $MsysRoot 'mingw64\bin');$env:PATH"
$arguments = @(
    (Join-Path $PSScriptRoot "benchmark-windows-gpu.py"),
    "--repo-root", $repoRoot,
    "--install-root", $installRoot,
    "--input", (Resolve-Path -LiteralPath $InputPath).Path,
    "--output-dir", $outputDir,
    "--decode-frames", $DecodeFrames,
    "--decode-repeats", $DecodeRepeats,
    "--encode-frames", $EncodeFrames,
    "--json-output", (Join-Path $outputDir "$ReportName.json"),
    "--markdown-output", (Join-Path $outputDir "$ReportName.md")
)
if ($SkipEncode) {
    $arguments += "--skip-encode"
}
& $python @arguments
if ($LASTEXITCODE -ne 0) {
    throw "Windows GPU benchmark failed with exit code $LASTEXITCODE"
}

Write-Host "Benchmark report: $(Join-Path $outputDir "$ReportName.md")"

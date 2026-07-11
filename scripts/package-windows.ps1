[CmdletBinding()]
param(
    [ValidateSet("Release", "Debug")]
    [string]$Configuration = "Release",
    [string]$MsysRoot = $(if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { "C:\msys64" }),
    [string]$OutputRoot,
    [switch]$SkipBuild,
    [switch]$VerifyGpu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$buildRoot = Join-Path $repoRoot "build"
$lockPath = Join-Path $PSScriptRoot "windows-build-lock.json"

if (-not $OutputRoot) {
    $OutputRoot = Join-Path $repoRoot "artifacts\windows"
} elseif (-not [IO.Path]::IsPathRooted($OutputRoot)) {
    $OutputRoot = Join-Path $repoRoot $OutputRoot
}
$OutputRoot = [IO.Path]::GetFullPath($OutputRoot)

function Get-GitValue {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)
    $value = & git -C $repoRoot @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed with exit code $LASTEXITCODE"
    }
    return ($value | Out-String).Trim()
}

function Remove-SafeStagingPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $outputPrefix = $OutputRoot.TrimEnd('\') + '\'
    if (-not $fullPath.StartsWith($outputPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a staging path outside the package output directory: $fullPath"
    }
    if (Test-Path -LiteralPath $fullPath) {
        Remove-Item -LiteralPath $fullPath -Recurse -Force
    }
}

if (-not $SkipBuild) {
    & (Join-Path $PSScriptRoot "build-windows.ps1") `
        -Configuration $Configuration `
        -MsysRoot $MsysRoot `
        -VerifyGpu:$VerifyGpu
}

$frozenRoot = Get-ChildItem -LiteralPath $buildRoot -Directory -Filter "exe.*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $frozenRoot -or -not (Test-Path -LiteralPath (Join-Path $frozenRoot.FullName "openshot-qt.exe") -PathType Leaf)) {
    throw "A frozen TeachCut build was not found under $buildRoot. Run without -SkipBuild first."
}

$commit = Get-GitValue @("rev-parse", "HEAD")
$shortCommit = Get-GitValue @("rev-parse", "--short=10", "HEAD")
$branch = Get-GitValue @("rev-parse", "--abbrev-ref", "HEAD")
$dirtyEntries = @(& git -C $repoRoot status --porcelain --untracked-files=normal)
if ($LASTEXITCODE -ne 0) {
    throw "Unable to determine Git working tree state."
}
$dirty = $dirtyEntries.Count -gt 0

$created = Get-Date
$stamp = $created.ToString("yyyyMMdd-HHmmss")
$dirtySuffix = if ($dirty) { "-dirty" } else { "" }
$packageName = "TeachCut-Windows-$stamp-$shortCommit$dirtySuffix"

New-Item -ItemType Directory -Path $OutputRoot -Force | Out-Null
$stagingRoot = Join-Path $OutputRoot (".staging-" + [guid]::NewGuid().ToString("N"))
$packageRoot = Join-Path $stagingRoot $packageName
$archivePath = Join-Path $OutputRoot "$packageName.zip"
$hashPath = "$archivePath.sha256"
$latestPath = Join-Path $OutputRoot "latest.json"

if (Test-Path -LiteralPath $archivePath) {
    throw "Package already exists: $archivePath"
}

try {
    New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
    Get-ChildItem -LiteralPath $frozenRoot.FullName -Force |
        Copy-Item -Destination $packageRoot -Recurse -Force

    $lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
    $manifest = [ordered]@{
        product = "TeachCut"
        platform = "windows-x64"
        configuration = $Configuration
        createdAt = $created.ToString("o")
        packageName = $packageName
        git = [ordered]@{
            commit = $commit
            shortCommit = $shortCommit
            branch = $branch
            dirty = $dirty
        }
        nativeSources = [ordered]@{
            libopenshot = $lock.libopenshot
            libopenshotAudio = $lock.libopenshotAudio
        }
        validatedToolchain = $lock.validatedToolchain
    }

    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    $manifestJson = $manifest | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText((Join-Path $packageRoot "build-manifest.json"), $manifestJson + "`n", $utf8NoBom)

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [IO.Compression.ZipFile]::CreateFromDirectory(
        $stagingRoot,
        $archivePath,
        [IO.Compression.CompressionLevel]::Optimal,
        $false
    )

    $archiveHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    [IO.File]::WriteAllText($hashPath, "$archiveHash  $([IO.Path]::GetFileName($archivePath))`n", $utf8NoBom)

    $latest = [ordered]@{
        packageName = $packageName
        archive = [IO.Path]::GetFileName($archivePath)
        sha256 = $archiveHash
        createdAt = $created.ToString("o")
        gitCommit = $commit
        dirty = $dirty
    } | ConvertTo-Json -Depth 4
    [IO.File]::WriteAllText($latestPath, $latest + "`n", $utf8NoBom)

    Write-Host "Windows package created: $archivePath"
    Write-Host "SHA256: $archiveHash"
    if ($dirty) {
        Write-Warning "The package contains uncommitted changes and is marked dirty."
    }
}
finally {
    Remove-SafeStagingPath $stagingRoot
}

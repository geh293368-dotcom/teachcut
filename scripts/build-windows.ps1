[CmdletBinding()]
param(
    [ValidateSet("Release", "Debug")]
    [string]$Configuration = "Release",
    [string]$MsysRoot = $(if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { "C:\msys64" }),
    [switch]$Bootstrap,
    [switch]$Clean,
    [switch]$SkipNative,
    [switch]$SkipTests,
    [switch]$SkipFreeze,
    [switch]$SkipSmoke,
    [switch]$VerifyGpu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$buildRoot = Join-Path $repoRoot "build"
$depsRoot = Join-Path $buildRoot "deps"
$nativeRoot = Join-Path $buildRoot "native"
$installRoot = Join-Path $buildRoot "install-x64"
$mingwBin = Join-Path $MsysRoot "mingw64\bin"
$python = Join-Path $mingwBin "python.exe"
$cmake = Join-Path $mingwBin "cmake.exe"
$pacman = Join-Path $MsysRoot "usr\bin\pacman.exe"
$lock = Get-Content (Join-Path $PSScriptRoot "windows-build-lock.json") -Raw | ConvertFrom-Json

function Invoke-External {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string[]]$ArgumentList
    )
    Write-Host "> $FilePath $($ArgumentList -join ' ')"
    & $FilePath @ArgumentList
    if ($LASTEXITCODE -ne 0) {
        throw "$FilePath failed with exit code $LASTEXITCODE"
    }
}

function Remove-SafeBuildPath {
    param([Parameter(Mandatory = $true)][string]$Path)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $fullBuildRoot = [IO.Path]::GetFullPath($buildRoot).TrimEnd('\') + '\'
    if (-not $fullPath.StartsWith($fullBuildRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a path outside the build directory: $fullPath"
    }
    if (Test-Path -LiteralPath $fullPath) {
        Remove-Item -LiteralPath $fullPath -Recurse -Force
    }
}

function Ensure-GitDependency {
    param(
        [Parameter(Mandatory = $true)]$Dependency,
        [Parameter(Mandatory = $true)][string]$Destination
    )
    if (-not (Test-Path -LiteralPath (Join-Path $Destination ".git"))) {
        New-Item -ItemType Directory -Path (Split-Path -Parent $Destination) -Force | Out-Null
        Invoke-External -FilePath "git" -ArgumentList @(
            "clone", "--filter=blob:none", "--no-checkout", $Dependency.repository, $Destination
        )
    }
    $currentRevision = (& git -C $Destination rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or $currentRevision.Trim() -ne $Dependency.revision) {
        Invoke-External -FilePath "git" -ArgumentList @(
            "-C", $Destination, "fetch", "--depth", "1", "origin", $Dependency.revision
        )
        Invoke-External -FilePath "git" -ArgumentList @(
            "-C", $Destination, "checkout", "--detach", $Dependency.revision
        )
    }
}

function Apply-DependencyPatch {
    param(
        [Parameter(Mandatory = $true)][string]$DependencyRoot,
        [Parameter(Mandatory = $true)][string]$PatchPath
    )
    & git -C $DependencyRoot apply --unidiff-zero --reverse --check $PatchPath 2>$null
    if ($LASTEXITCODE -eq 0) {
        return
    }
    Invoke-External -FilePath "git" -ArgumentList @(
        "-C", $DependencyRoot, "apply", "--unidiff-zero", "--whitespace=nowarn", $PatchPath
    )
}

if ($Bootstrap) {
    if (-not (Test-Path -LiteralPath $pacman -PathType Leaf)) {
        throw "MSYS2 was not found at $MsysRoot. Install MSYS2 first or pass -MsysRoot."
    }
    $packages = Get-Content (Join-Path $PSScriptRoot "windows-msys2-packages.txt") |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith("#") }
    Invoke-External -FilePath $pacman -ArgumentList (@("-S", "--needed", "--noconfirm") + $packages)
    Invoke-External -FilePath $python -ArgumentList @(
        "-m", "pip", "install", "--break-system-packages", "-r",
        (Join-Path $PSScriptRoot "windows-requirements.txt")
    )
}

foreach ($requiredTool in @($python, $cmake, (Join-Path $mingwBin "ninja.exe"))) {
    if (-not (Test-Path -LiteralPath $requiredTool -PathType Leaf)) {
        throw "Required Windows build tool was not found: $requiredTool. Run with -Bootstrap first."
    }
}

$env:PATH = "$installRoot\bin;$mingwBin;$env:PATH"
$env:PYTHONPATH = "$installRoot\python;$repoRoot\src"
$env:QT_QPA_PLATFORM = "offscreen"

if ($Clean) {
    Remove-SafeBuildPath $nativeRoot
    Remove-SafeBuildPath $installRoot
    Get-ChildItem $buildRoot -Directory -ErrorAction SilentlyContinue |
        Where-Object Name -Like "exe.*" |
        ForEach-Object { Remove-SafeBuildPath $_.FullName }
}

if (-not $SkipNative) {
    $audioSource = Join-Path $depsRoot "libopenshot-audio"
    $libSource = Join-Path $depsRoot "libopenshot"
    Ensure-GitDependency $lock.libopenshotAudio $audioSource
    Ensure-GitDependency $lock.libopenshot $libSource
    Apply-DependencyPatch $libSource (Join-Path $PSScriptRoot "patches\libopenshot-gcc16-cstdint.patch")
    Apply-DependencyPatch $libSource (Join-Path $PSScriptRoot "patches\libopenshot-modern-hardware-decode.patch")
    Apply-DependencyPatch $libSource (Join-Path $PSScriptRoot "patches\libopenshot-modern-nvenc-options.patch")

    $audioBuild = Join-Path $nativeRoot "audio"
    $libBuild = Join-Path $nativeRoot "libopenshot"
    Invoke-External -FilePath $cmake -ArgumentList @(
        "-S", $audioSource,
        "-B", $audioBuild,
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=$Configuration",
        "-DCMAKE_INSTALL_PREFIX=$installRoot",
        "-DCMAKE_CXX_FLAGS=-DJUCE_ASIO=0",
        "-DBUILD_TESTING=OFF",
        "-DENABLE_AUDIO_DOCS=OFF"
    )
    Invoke-External -FilePath $cmake -ArgumentList @(
        "--build", $audioBuild, "--config", $Configuration, "--target", "install"
    )

    Invoke-External -FilePath $cmake -ArgumentList @(
        "-S", $libSource,
        "-B", $libBuild,
        "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=$Configuration",
        "-DCMAKE_INSTALL_PREFIX=$installRoot",
        "-DCMAKE_PREFIX_PATH=$installRoot",
        "-DOpenShotAudio_ROOT=$installRoot",
        "-DPYTHON_EXECUTABLE=$python",
        "-DPython3_EXECUTABLE=$python",
        "-DENABLE_PYTHON=ON",
        "-DENABLE_RUBY=OFF",
        "-DENABLE_JAVA=OFF",
        "-DENABLE_LIB_DOCS=OFF",
        "-DBUILD_TESTING=OFF",
        "-DENABLE_MAGICK=OFF",
        "-DENABLE_OPENCV=ON",
        "-DUSE_HW_ACCEL=ON",
        "-DUSE_QT6=OFF",
        "-DUSE_SYSTEM_JSONCPP=ON"
    )
    Invoke-External -FilePath $cmake -ArgumentList @(
        "--build", $libBuild, "--config", $Configuration, "--target", "install"
    )
}

if (-not $SkipTests) {
    & (Join-Path $PSScriptRoot "test-windows.ps1") -MsysRoot $MsysRoot -InstallRoot $installRoot
}

if (-not $SkipFreeze) {
    Push-Location $repoRoot
    try {
        Invoke-External -FilePath $python -ArgumentList @("freeze.py", "build")
    }
    finally {
        Pop-Location
    }
}

if (-not $SkipSmoke) {
    & (Join-Path $PSScriptRoot "smoke-test-windows.ps1") `
        -MsysRoot $MsysRoot `
        -InstallRoot $installRoot `
        -VerifyGpu:$VerifyGpu
}

Write-Host "Windows build pipeline completed successfully."

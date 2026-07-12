[CmdletBinding()]
param(
    [ValidateSet("Release", "Debug")]
    [string]$Configuration = "Release",
    [ValidateSet(5, 6)]
    [int]$QtMajor = 6,
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
$sourceRoot = Join-Path $repoRoot "native"
$nativeRoot = if ($QtMajor -eq 5) { Join-Path $buildRoot "native" } else { Join-Path $buildRoot "native-qt6" }
$installRoot = if ($QtMajor -eq 5) { Join-Path $buildRoot "install-x64" } else { Join-Path $buildRoot "install-x64-qt6" }
$bundleRoot = Join-Path $buildRoot "exe.qt$QtMajor"
$mingwRoot = Join-Path $MsysRoot "mingw64"
$mingwBin = Join-Path $mingwRoot "bin"
$python = Join-Path $mingwBin "python.exe"
$cmake = Join-Path $mingwBin "cmake.exe"
$pacman = Join-Path $MsysRoot "usr\bin\pacman.exe"
$protobufInclude = Join-Path $mingwRoot "include"
$protobufLibrary = Join-Path $mingwRoot "lib\libprotobuf.dll.a"
$protobufProtoc = Join-Path $mingwBin "protoc.exe"

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

if ($Bootstrap) {
    if (-not (Test-Path -LiteralPath $pacman -PathType Leaf)) {
        throw "MSYS2 was not found at $MsysRoot. Install MSYS2 first or pass -MsysRoot."
    }
    $packageList = Join-Path $PSScriptRoot "windows-msys2-packages-qt$QtMajor.txt"
    if (-not (Test-Path -LiteralPath $packageList -PathType Leaf)) {
        throw "Qt $QtMajor package list was not found: $packageList"
    }
    $packages = Get-Content $packageList |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ -and -not $_.StartsWith("#") }
    Invoke-External -FilePath $pacman -ArgumentList (@("-S", "--needed", "--noconfirm") + $packages)
    Invoke-External -FilePath $python -ArgumentList @(
        "-m", "pip", "install", "--break-system-packages", "-r",
        (Join-Path $PSScriptRoot "windows-requirements.txt")
    )
}

foreach ($requiredTool in @(
    $python,
    $cmake,
    (Join-Path $mingwBin "ninja.exe"),
    $protobufLibrary,
    $protobufProtoc
)) {
    if (-not (Test-Path -LiteralPath $requiredTool -PathType Leaf)) {
        throw "Required Windows build tool was not found: $requiredTool. Run with -Bootstrap first."
    }
}

$env:PATH = "$installRoot\bin;$mingwBin;$env:PATH"
$env:PYTHONPATH = "$installRoot\python;$repoRoot\src"
$env:QT_QPA_PLATFORM = "offscreen"
$env:OPENSHOT_QT_API = "pyqt$QtMajor"
$env:OPENSHOT_ARTIFACT_PATH = $installRoot
$env:OPENSHOT_FREEZE_BUILD_DIR = $bundleRoot

if ($Clean) {
    Remove-SafeBuildPath $nativeRoot
    Remove-SafeBuildPath $installRoot
    Remove-SafeBuildPath $bundleRoot
}

$bindingCheck = @'
import qt_api
expected = "pyqt6" if __import__("os").environ["OPENSHOT_QT_API"] == "pyqt6" else "pyqt5"
if qt_api.QT_API != expected:
    raise SystemExit(f"Expected {expected}, selected {qt_api.QT_API}")
print(f"qt.binding={qt_api.QT_API}; qt.version={qt_api.QT_VERSION_STR}; binding.version={qt_api.BINDING_VERSION_STR}")
'@
Invoke-External -FilePath $python -ArgumentList @("-c", $bindingCheck)

if (-not $SkipNative) {
    $audioSource = Join-Path $sourceRoot "libopenshot-audio"
    $libSource = Join-Path $sourceRoot "libopenshot"
    foreach ($requiredSource in @($audioSource, $libSource)) {
        if (-not (Test-Path -LiteralPath (Join-Path $requiredSource "CMakeLists.txt") -PathType Leaf)) {
            throw "Required native source tree was not found: $requiredSource"
        }
    }

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
        "-DUSE_QT6=$(if ($QtMajor -eq 6) { 'ON' } else { 'OFF' })",
        "-DUSE_SYSTEM_JSONCPP=ON",
        "-DProtobuf_INCLUDE_DIR=$protobufInclude",
        "-DProtobuf_LIBRARY_RELEASE=$protobufLibrary",
        "-DProtobuf_LIBRARY_DEBUG=$protobufLibrary",
        "-DProtobuf_PROTOC_EXECUTABLE=$protobufProtoc"
    )

    # GitHub Windows runners also ship MySQL, whose MSVC libprotobuf.lib can
    # otherwise win CMake's search ahead of the MSYS2 MinGW import library.
    $cmakeCache = Join-Path $libBuild "CMakeCache.txt"
    $protobufCacheEntries = Get-Content -LiteralPath $cmakeCache |
        Where-Object { $_ -match '^Protobuf_LIBRARY_(DEBUG|RELEASE):FILEPATH=' }
    if (-not $protobufCacheEntries) {
        throw "CMake did not record a Protobuf library in $cmakeCache"
    }
    $expectedProtobufLibrary = [IO.Path]::GetFullPath($protobufLibrary)
    foreach ($entry in $protobufCacheEntries) {
        $selectedLibrary = ($entry -split '=', 2)[1]
        if (-not $selectedLibrary -or
            -not [IO.Path]::GetFullPath($selectedLibrary).Equals(
                $expectedProtobufLibrary,
                [StringComparison]::OrdinalIgnoreCase
            )) {
            throw "CMake selected an unexpected Protobuf library: $selectedLibrary (expected $expectedProtobufLibrary)"
        }
    }

    Invoke-External -FilePath $cmake -ArgumentList @(
        "--build", $libBuild, "--config", $Configuration, "--target", "install"
    )
}

if (-not $SkipTests) {
    & (Join-Path $PSScriptRoot "test-windows.ps1") -MsysRoot $MsysRoot -InstallRoot $installRoot
}

if (-not $SkipFreeze) {
    # cx_Freeze does not guarantee that an existing output directory is purged.
    # Always start from an empty binding-specific bundle to avoid mixing Qt majors.
    Remove-SafeBuildPath $bundleRoot
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
        -BundleRoot $bundleRoot `
        -VerifyGpu:$VerifyGpu
}

Write-Host "Windows Qt $QtMajor build pipeline completed successfully."

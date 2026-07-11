[CmdletBinding()]
param(
    [string]$MsysRoot = $(if ($env:MSYS2_ROOT) { $env:MSYS2_ROOT } else { "C:\msys64" }),
    [string]$InstallRoot = "",
    [string]$BundleRoot = "",
    [switch]$VerifyGpu
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $InstallRoot) {
    $InstallRoot = Join-Path $repoRoot "build\install-x64"
}
$python = Join-Path $MsysRoot "mingw64\bin\python.exe"
$env:PATH = "$(Join-Path $InstallRoot 'bin');$(Join-Path $MsysRoot 'mingw64\bin');$env:PATH"
$env:PYTHONPATH = "$(Join-Path $InstallRoot 'python');$(Join-Path $repoRoot 'src')"
$env:QT_QPA_PLATFORM = "offscreen"
# Keep automated UI validation independent of the user's in-app UI scale.
$env:OPENSHOT_UI_SCALE = "1.0"

$verifyArgs = @(
    (Join-Path $PSScriptRoot "verify_windows_runtime.py"),
    "--repo-root", $repoRoot,
    "--install-root", $InstallRoot
)
if ($VerifyGpu) {
    $verifyArgs += "--verify-gpu"
}
& $python @verifyArgs
if ($LASTEXITCODE -ne 0) {
    throw "Native Windows runtime verification failed with exit code $LASTEXITCODE"
}

$bundle = if ($BundleRoot) {
    Get-Item -LiteralPath $BundleRoot -ErrorAction SilentlyContinue
} else {
    Get-ChildItem (Join-Path $repoRoot "build") -Directory |
        Where-Object Name -Like "exe.*" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}
if (-not $bundle) {
    throw "No cx_Freeze bundle was found under build\exe.*"
}
$exe = Join-Path $bundle.FullName "openshot-qt.exe"
if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) {
    throw "Frozen launcher was not found: $exe"
}

$cliExe = Join-Path $bundle.FullName "openshot-qt-cli.exe"
if (-not (Test-Path -LiteralPath $cliExe -PathType Leaf)) {
    throw "Frozen console launcher was not found: $cliExe"
}
$version = & $cliExe --version
if ($LASTEXITCODE -ne 0 -or -not $version) {
    throw "Frozen launcher version check failed"
}
Write-Host "frozen.version=$version"

$stdout = Join-Path $repoRoot "build\windows-smoke.stdout.log"
$stderr = Join-Path $repoRoot "build\windows-smoke.stderr.log"
Remove-Item -LiteralPath $stdout, $stderr -Force -ErrorAction SilentlyContinue
$process = Start-Process -FilePath $exe -WorkingDirectory $bundle.FullName `
    -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
$exited = $process.WaitForExit(8000)
if ($exited) {
    $errorText = if (Test-Path -LiteralPath $stderr) { Get-Content -LiteralPath $stderr -Raw } else { "" }
    throw "Frozen GUI exited during the smoke window (exit=$($process.ExitCode)). $errorText"
}
Stop-Process -Id $process.Id -Force
Write-Host "frozen.gui=started"

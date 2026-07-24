param(
    [string]$SourceBundle = "D:\CitadexBuilds\Citadex-Local-0.2.0-windows-x64",
    [string]$OutputRoot = "D:\CitadexBuilds\installer",
    [string]$InnoCompiler = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$ScriptPath = Join-Path $ProjectRoot "CitadexLocalSetup.iss"

if (-not (Test-Path -LiteralPath (Join-Path $SourceBundle "Citadex-Local.exe"))) {
    throw "Portable Citadex bundle not found: $SourceBundle"
}
if (-not (Test-Path -LiteralPath (Join-Path $SourceBundle "models"))) {
    throw "Bundled model directory not found: $SourceBundle\models"
}

if (-not $InnoCompiler) {
    $Candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 7\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    )
    $InnoCompiler = $Candidates |
        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
        Select-Object -First 1
}
if (-not $InnoCompiler) {
    throw "Inno Setup 7 compiler not found. Install it from https://jrsoftware.org/isdl.php"
}

New-Item -ItemType Directory -Force -Path $OutputRoot | Out-Null
& $InnoCompiler `
    "/DSourceBundle=$([System.IO.Path]::GetFullPath($SourceBundle))" `
    "/DSetupOutput=$([System.IO.Path]::GetFullPath($OutputRoot))" `
    $ScriptPath
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup failed with exit code $LASTEXITCODE."
}

$Installer = Get-ChildItem -LiteralPath $OutputRoot -Filter "Citadex-Local-Setup-*.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if (-not $Installer) {
    throw "Installer output was not created."
}
$Hash = (Get-FileHash -LiteralPath $Installer.FullName -Algorithm SHA256).Hash
Set-Content -LiteralPath "$($Installer.FullName).sha256" -Encoding ascii -NoNewline `
    -Value "$Hash  $($Installer.Name)"

Write-Host ""
Write-Host "Citadex Local installer complete:"
Write-Host "  Setup:   $($Installer.FullName)"
Write-Host "  SHA-256: $Hash"


# install_alias.ps1 — Register global 'Citadex' command in PowerShell profile
# Usage: powershell -ExecutionPolicy Bypass -File install_alias.ps1

$aliasFunc = @'
function Citadex {
    param([Parameter(ValueFromRemainingArguments=$true)][string[]]$args)
    python D:\copilot\my-ai-copilot\gui.py @args
}
'@

# Ensure profile directory exists
$profileDir = Split-Path $PROFILE
if (!(Test-Path $profileDir)) {
    New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    Write-Host "Created profile directory: $profileDir" -ForegroundColor Green
}

# Ensure profile file exists
if (!(Test-Path $PROFILE)) {
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    Write-Host "Created profile file: $PROFILE" -ForegroundColor Green
}

# Check if already installed
$currentContent = Get-Content $PROFILE -Raw -ErrorAction SilentlyContinue
if ($currentContent -and $currentContent.Contains("function Citadex")) {
    Write-Host "✅ Citadex alias already installed in: $PROFILE" -ForegroundColor Cyan
} else {
    # Append alias to profile
    Add-Content -Path $PROFILE -Value "`n$aliasFunc"
    Write-Host "✅ Citadex alias installed to: $PROFILE" -ForegroundColor Green
}

Write-Host ""
Write-Host "🚀 Usage:" -ForegroundColor Yellow
Write-Host "   Citadex              → Launch Citadex GUI" -ForegroundColor White
Write-Host "   Restart your terminal, then run: Citadex" -ForegroundColor Gray

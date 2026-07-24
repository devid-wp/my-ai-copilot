param(
    [string]$OutputRoot = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Version = "0.2.1"
$BundleName = "Citadex-Local-$Version-windows-x64"
$LlamaTag = "b10092"
$LlamaArchive = "llama-$LlamaTag-bin-win-cpu-x64.zip"
$LlamaUrl = "https://github.com/ggml-org/llama.cpp/releases/download/$LlamaTag/$LlamaArchive"
$ModelName = "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
$ModelUrl = "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/${ModelName}?download=true"
$ModelSha256 = "cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046"
$RequiredBytes = 5GB

if (-not $OutputRoot) {
    $ProjectDrive = [System.IO.DriveInfo]::new((Split-Path -Qualifier $ProjectRoot))
    if ($ProjectDrive.AvailableFreeSpace -ge $RequiredBytes) {
        $OutputRoot = Join-Path $ProjectRoot "dist-local"
    } else {
        $BestDrive = [System.IO.DriveInfo]::GetDrives() |
            Where-Object { $_.IsReady -and $_.DriveType -eq "Fixed" } |
            Sort-Object AvailableFreeSpace -Descending |
            Select-Object -First 1
        if (-not $BestDrive -or $BestDrive.AvailableFreeSpace -lt $RequiredBytes) {
            throw "At least 5 GB of free disk space is required."
        }
        $OutputRoot = Join-Path $BestDrive.RootDirectory.FullName "CitadexBuilds"
    }
}

$OutputRoot = [System.IO.Path]::GetFullPath($OutputRoot)
$Bundle = Join-Path $OutputRoot $BundleName
$DownloadCache = Join-Path $OutputRoot "downloads"
$RuntimeArchive = Join-Path $DownloadCache $LlamaArchive
$RuntimeExtract = Join-Path $DownloadCache "llama-$LlamaTag"
$CachedModel = Join-Path $DownloadCache $ModelName
$ModelPath = Join-Path $Bundle "models\$ModelName"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Run setup.bat before building Citadex Local."
}

New-Item -ItemType Directory -Force -Path $OutputRoot, $DownloadCache | Out-Null

Write-Host "Building Citadex Local executable..."
& $Python -m PyInstaller --noconfirm --clean (Join-Path $ProjectRoot "CitadexLocal.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

if (-not (Test-Path -LiteralPath $RuntimeArchive)) {
    Write-Host "Downloading llama.cpp $LlamaTag..."
    & curl.exe --fail --location --retry 3 --output $RuntimeArchive $LlamaUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download llama.cpp (curl exit code $LASTEXITCODE)."
    }
}
if (Test-Path -LiteralPath $RuntimeExtract) {
    Remove-Item -LiteralPath $RuntimeExtract -Recurse -Force
}
Expand-Archive -LiteralPath $RuntimeArchive -DestinationPath $RuntimeExtract
$Server = Get-ChildItem -LiteralPath $RuntimeExtract -Filter "llama-server.exe" -Recurse |
    Select-Object -First 1
if (-not $Server) {
    throw "llama-server.exe was not found in $LlamaArchive."
}

if (Test-Path -LiteralPath $Bundle) {
    Remove-Item -LiteralPath $Bundle -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $Bundle, (Join-Path $Bundle "runtime"), (Join-Path $Bundle "models") | Out-Null
Copy-Item -Path (Join-Path $Server.Directory.FullName "*") -Destination (Join-Path $Bundle "runtime") -Recurse
Copy-Item -LiteralPath (Join-Path $ProjectRoot "dist\Citadex-Local.exe") -Destination $Bundle
Copy-Item -LiteralPath (Join-Path $ProjectRoot "README.md") -Destination $Bundle
Copy-Item -LiteralPath (Join-Path $ProjectRoot "LICENSE") -Destination (Join-Path $Bundle "CITADEX-LICENSE.txt")
Invoke-WebRequest `
    -Uri "https://raw.githubusercontent.com/ggml-org/llama.cpp/$LlamaTag/LICENSE" `
    -OutFile (Join-Path $Bundle "LLAMA-CPP-LICENSE.txt")

if (-not (Test-Path -LiteralPath $CachedModel)) {
    Write-Host "Downloading Qwen2.5-Coder 1.5B Q4_K_M (about 1.1 GB)..."
    & curl.exe --fail --location --retry 5 --continue-at - --output $CachedModel $ModelUrl
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to download Qwen model (curl exit code $LASTEXITCODE)."
    }
}
$ActualModelHash = (Get-FileHash -LiteralPath $CachedModel -Algorithm SHA256).Hash.ToLowerInvariant()
if ($ActualModelHash -ne $ModelSha256) {
    throw "Model checksum mismatch. Expected $ModelSha256, got $ActualModelHash."
}
Copy-Item -LiteralPath $CachedModel -Destination $ModelPath

$ModelLicense = Join-Path $Bundle "QWEN-LICENSE.txt"
Invoke-WebRequest `
    -Uri "https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/LICENSE" `
    -OutFile $ModelLicense

$Archive = Join-Path $OutputRoot "$BundleName.zip"
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Write-Host "Creating portable archive..."
Compress-Archive -Path (Join-Path $Bundle "*") -DestinationPath $Archive -CompressionLevel Optimal
$ArchiveHash = (Get-FileHash -LiteralPath $Archive -Algorithm SHA256).Hash
$ChecksumFile = "$Archive.sha256"
Set-Content -LiteralPath $ChecksumFile -Encoding ascii -NoNewline -Value "$ArchiveHash  $BundleName.zip"

Write-Host ""
Write-Host "Citadex Local build complete:"
Write-Host "  Folder:   $Bundle"
Write-Host "  Archive:  $Archive"
Write-Host "  SHA-256:  $ArchiveHash"

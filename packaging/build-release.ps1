# Build the portable hackathon release zip.
# Output: release\MusicDiscovery-win64.zip
# The zip contains a prebuilt frontend (no Node needed at runtime), the
# Python sources with pinned uv.lock, a bundled uv.exe when available, and
# ffmpeg/ffprobe when found on PATH. It contains no music and no index.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$stage = Join-Path $root "release\MusicDiscovery"
$zip = Join-Path $root "release\MusicDiscovery-win64.zip"

Write-Host "Building frontend..."
Push-Location (Join-Path $root "web")
try {
    if (-not (Test-Path "node_modules")) { npm install }
    npm run build
} finally { Pop-Location }

if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force $stage | Out-Null

Copy-Item (Join-Path $root "src") $stage -Recurse
Copy-Item (Join-Path $root "pyproject.toml") $stage
Copy-Item (Join-Path $root "uv.lock") $stage
New-Item -ItemType Directory -Force (Join-Path $stage "web") | Out-Null
Copy-Item (Join-Path $root "web\dist") (Join-Path $stage "web") -Recurse
Copy-Item (Join-Path $PSScriptRoot "MusicDiscovery.bat") $stage
Copy-Item (Join-Path $PSScriptRoot "JUDGE-README.txt") $stage

$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    Copy-Item $uv.Source (Join-Path $stage "uv.exe")
    Write-Host "Bundled uv from $($uv.Source)"
} else {
    Write-Warning "uv not found on PATH: the launcher will need uv installed on the judge machine."
}

foreach ($tool in "ffmpeg", "ffprobe") {
    $cmd = Get-Command $tool -ErrorAction SilentlyContinue
    if ($cmd) {
        Copy-Item $cmd.Source (Join-Path $stage "$tool.exe")
        Write-Host "Bundled $tool from $($cmd.Source)"
    } else {
        Write-Warning "$tool not found on PATH: release is NOT shippable until it is bundled."
    }
}

New-Item -ItemType Directory -Force (Join-Path $stage "data") | Out-Null
"Your index will be created here on first run. No music is included in this package." |
    Set-Content (Join-Path $stage "data\README.txt")

if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $stage -DestinationPath $zip
$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Wrote $zip ($size MB)"

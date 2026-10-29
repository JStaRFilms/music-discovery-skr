@echo off
title Music Discovery - local library search
cd /d "%~dp0"
echo Starting Music Discovery on http://127.0.0.1:8765
echo Your browser will open when the server is ready. Keep this window open while you use the app.
if not exist "web\dist\index.html" (
  echo Building the interface for the first run...
  pushd web && call npm install && call npm run build && popd
)
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 60;$i++){ try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/api/status -TimeoutSec 2 | Out-Null; Start-Process 'http://127.0.0.1:8765'; break } catch { Start-Sleep -Seconds 1 } }"
uv run --extra embed --extra app python -m music_discovery.server
pause

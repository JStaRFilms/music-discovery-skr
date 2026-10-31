@echo off
title Music Discovery
cd /d "%~dp0"
if not exist "data\index" mkdir "data\index"
set "MUSIC_DISCOVERY_DATA=%CD%\data"
if exist "uv.exe" set "UV=%CD%\uv.exe"
if not defined UV set "UV=uv"
if exist "ffmpeg.exe" set "PATH=%CD%;%PATH%"
echo Starting Music Discovery on http://127.0.0.1:8765
echo First run installs the app environment and downloads the search model (about 2 GB). Later runs start fast.
echo Keep this window open while you use the app.
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "for($i=0;$i -lt 120;$i++){ try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8765/api/status -TimeoutSec 2 | Out-Null; Start-Process 'http://127.0.0.1:8765'; break } catch { Start-Sleep -Seconds 2 } }"
"%UV%" run --extra embed --extra app python -m music_discovery.server
pause

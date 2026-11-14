@echo off
setlocal
cd /d "%~dp0"
python start.py %*
if errorlevel 1 (
    echo.
    echo Press any key to exit...
    pause >nul
)

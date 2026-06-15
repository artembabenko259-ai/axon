@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 "%~dp0main.py" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python "%~dp0main.py" %*
    exit /b %ERRORLEVEL%
)

echo [AXON] Python 3 was not found. Install Python 3.10+ and ensure py or python is on PATH.
exit /b 1

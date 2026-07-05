@echo off
setlocal EnableExtensions
set "AXON_HOME=%~dp0"
set "UAR_CLI=%AXON_HOME%uar.py"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 "%UAR_CLI%" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python "%UAR_CLI%" %*
    exit /b %ERRORLEVEL%
)

echo [UAR] Python 3 was not found. Install Python 3.10+ and ensure py or python is on PATH.
exit /b 1

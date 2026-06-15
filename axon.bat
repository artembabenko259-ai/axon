@echo off
setlocal EnableExtensions
set "AXON_HOME=%~dp0"
set "AXON_CLI=%AXON_HOME%cli.py"

where py >nul 2>&1
if %ERRORLEVEL%==0 (
    py -3 "%AXON_CLI%" %*
    exit /b %ERRORLEVEL%
)

where python >nul 2>&1
if %ERRORLEVEL%==0 (
    python "%AXON_CLI%" %*
    exit /b %ERRORLEVEL%
)

echo [AXON] Python 3 was not found. Install Python 3.10+ and ensure py or python is on PATH.
exit /b 1

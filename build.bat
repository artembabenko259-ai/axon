@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ============================================================================
REM  AXON One-Click Master Builder
REM  PyInstaller -> Inno Setup -> release/ + SHA-256 + Winget manifest patch
REM ============================================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
cd /d "%ROOT%"

set "VERSION=1.0.1"
set "SETUP_NAME=AXON_Setup_v%VERSION%.exe"
set "RELEASE_DIR=%ROOT%\release"
set "VENV_PY=%ROOT%\.venv-build\Scripts\python.exe"
set "ISCC="

echo.
echo ========================================================================
echo   AXON Master Builder v%VERSION%
echo ========================================================================
echo.

REM --- Step 0: App icon (ICO for exe + installer) ---------------------------
if not exist "%ROOT%\assets\axon.ico" (
    echo [0/6] Building axon.ico ...
    "%VENV_PY%" "%ROOT%\scripts\build_icon.py"
    if errorlevel 1 goto :fail
) else (
    echo [0/6] Using assets\axon.ico
)

REM --- Step 1: Python venv (lean PyInstaller, no manual setup) ---------------
if not exist "%VENV_PY%" (
    echo [1/6] Creating build virtualenv .venv-build ...
    python -m venv "%ROOT%\.venv-build"
    if errorlevel 1 goto :fail
    "%VENV_PY%" -m pip install --upgrade pip -q
    "%VENV_PY%" -m pip install -r "%ROOT%\requirements.txt" -q
    "%VENV_PY%" -m pip install -r "%ROOT%\requirements-build.txt" -q
    if errorlevel 1 goto :fail
) else (
    echo [1/6] Using existing .venv-build
)

REM --- Step 1: Zenith panel (Next.js standalone + portable Node) ------------
echo.
echo [2/6] Building Zenith control panel ...
"%VENV_PY%" "%ROOT%\scripts\build_zenith.py"
if errorlevel 1 goto :fail
if not exist "%ROOT%\build\bundle-staging\zenith-web\server.js" (
    echo [ERROR] build\bundle-staging\zenith-web\server.js was not created.
    goto :fail
)

REM --- Step 2.5: Compile Go-based TUI client ---------------------------------
where go >nul 2>nul
if %errorlevel% equ 0 (
    echo.
    echo [2.5/6] Building Go-based TUI client ^(axon-shard.exe^) ...
    cd "%ROOT%\shard"
    go build -o "%ROOT%\axon-shard.exe"
    cd "%ROOT%"
) else (
    echo.
    echo [2.5/6] Go not found in PATH, skipping Go compilation.
)

REM --- Step 3: PyInstaller ---------------------------------------------------
echo.
echo [3/6] Building axon.exe with PyInstaller ...
"%VENV_PY%" "%ROOT%\scripts\build_exe.py" --clean
if errorlevel 1 goto :fail
if not exist "%ROOT%\dist\exe\axon\axon.exe" (
    echo [ERROR] dist\exe\axon\axon.exe was not created.
    goto :fail
)

if exist "%ROOT%\axon-shard.exe" (
    copy /y "%ROOT%\axon-shard.exe" "%ROOT%\dist\exe\axon\axon-shard.exe" >nul
)


REM --- Step 2: Locate Inno Setup compiler ------------------------------------
echo.
echo [4/6] Locating Inno Setup compiler (ISCC.exe) ...

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" (
    set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
)
if not defined ISCC if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
)
if not defined ISCC (
    for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do (
        set "ISCC=%%I"
        goto :found_iscc
    )
)
:found_iscc

if not defined ISCC (
    echo [ERROR] Inno Setup 6 not found.
    echo         Install from: https://jrsoftware.org/isinfo.php
    echo         Expected:    C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe
    goto :fail
)
echo         Found: !ISCC!

REM --- Step 3: Compile installer (silent ISCC) ---------------------------------
echo.
echo [5/6] Compiling installer.iss ...
"!ISCC!" /Q "%ROOT%\scripts\installer.iss"
if errorlevel 1 goto :fail
if not exist "%ROOT%\dist\setup\%SETUP_NAME%" (
    echo [ERROR] dist\setup\%SETUP_NAME% was not created.
    goto :fail
)

REM --- Step 4: Move to release/ + hash + patch Winget manifest ----------------
echo.
echo [6/6] Publishing to release\ and computing SHA-256 ...

if not exist "%RELEASE_DIR%" mkdir "%RELEASE_DIR%"
copy /Y "%ROOT%\dist\setup\%SETUP_NAME%" "%RELEASE_DIR%\%SETUP_NAME%" >nul
if errorlevel 1 goto :fail

"%VENV_PY%" "%ROOT%\scripts\hash_setup.py" --setup "%RELEASE_DIR%\%SETUP_NAME%" --patch-manifest
if errorlevel 1 goto :fail

echo.
echo ========================================================================
echo   BUILD COMPLETE
echo ========================================================================
echo   Installer : release\%SETUP_NAME%
for %%A in ("%RELEASE_DIR%\%SETUP_NAME%") do echo   Size      : %%~zA bytes
echo.
echo   Winget manifest patched: winget\Core.AXON.installer.yaml
echo   Next: upload release\%SETUP_NAME% to GitHub Releases and set InstallerUrl
echo ========================================================================
echo.
exit /b 0

:fail
echo.
echo [FAILED] Master build aborted.
exit /b 1

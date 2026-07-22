@echo off
:: ============================================================
:: HP Semiconductor Analyzer Controller — EXE Build Script
:: Double-click this file or run from Command Prompt.
::
:: Usage:
::   build_exe.bat               — portable folder only
::   build_exe.bat /installer    — portable folder + setup EXE
::   build_exe.bat /clean        — clean before building
::   build_exe.bat /installer /clean  — clean + everything
::
:: For a setup EXE (/installer) you need Inno Setup 6:
::   https://jrsoftware.org/isdl.php
:: ============================================================

setlocal enabledelayedexpansion
set APPNAME=HP_Analyzer
set VENV=.venv_build
set DO_INSTALLER=0
set DO_CLEAN=0

:: Parse arguments
for %%A in (%*) do (
    if /I "%%A"=="/installer" set DO_INSTALLER=1
    if /I "%%A"=="/clean"     set DO_CLEAN=1
)

echo.
echo ============================================================
echo   HP Semiconductor Analyzer  ^|  EXE Builder
echo ============================================================
echo.

:: ── Locate Python ─────────────────────────────────────────────────────────────
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found.  Install from https://python.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [OK] %%v

:: ── Optional clean ────────────────────────────────────────────────────────────
if %DO_CLEAN%==1 (
    echo [..] Cleaning previous build artefacts...
    if exist build      rmdir /s /q build
    if exist dist       rmdir /s /q dist
    if exist %VENV%     rmdir /s /q %VENV%
    echo [OK] Clean complete.
)

:: ── Virtual environment ───────────────────────────────────────────────────────
if not exist "%VENV%\Scripts\python.exe" (
    echo [..] Creating virtual environment...
    python -m venv %VENV%
    if %errorlevel% neq 0 ( echo [ERROR] venv failed & pause & exit /b 1 )
)
echo [OK] Virtual environment ready.

:: ── Install dependencies ──────────────────────────────────────────────────────
echo [..] Installing dependencies (first run may take ~5 min)...
%VENV%\Scripts\pip install --upgrade pip --quiet
%VENV%\Scripts\pip install -r requirements.txt --quiet
%VENV%\Scripts\pip install pyinstaller pyinstaller-hooks-contrib openpyxl --quiet
if %errorlevel% neq 0 ( echo [ERROR] pip install failed & pause & exit /b 1 )
echo [OK] Dependencies installed.

:: ── Generate version from git tag ────────────────────────────────────────────
echo [..] Reading version from git tag...
%VENV%\Scripts\python scripts\gen_version.py
if %errorlevel% neq 0 ( echo [WARN] gen_version.py failed - using src/version.py fallback )

:: Extract version string for filenames
for /f "tokens=*" %%v in ('%VENV%\Scripts\python -c "import sys; sys.path.insert(0,chr(46)); from src.version import __version__; print(__version__)"') do (
    set VERSION=%%v
)
echo [OK] Version: !VERSION!

:: ── Run PyInstaller ───────────────────────────────────────────────────────────
echo [..] Running PyInstaller (2-5 minutes)...
%VENV%\Scripts\python -m PyInstaller hp_analyzer.spec --noconfirm
if %errorlevel% neq 0 ( echo [ERROR] PyInstaller failed & pause & exit /b 1 )
echo [OK] PyInstaller build complete  →  dist\%APPNAME%\

:: ── Inno Setup installer (optional) ──────────────────────────────────────────
if %DO_INSTALLER%==1 (
    echo.
    echo [..] Looking for Inno Setup 6...
    set ISCC=
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe
    ) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set ISCC=C:\Program Files\Inno Setup 6\ISCC.exe
    )

    if "!ISCC!"=="" (
        echo [WARN] Inno Setup 6 not found - skipping installer step.
        echo        Install from https://jrsoftware.org/isdl.php
    ) else (
        echo [OK] Found ISCC: !ISCC!
        if not exist release mkdir release
        "!ISCC!" installer.iss
        if %errorlevel% neq 0 ( echo [ERROR] Inno Setup failed & pause & exit /b 1 )
        echo [OK] Installer  →  release\HP_Analyzer_v!VERSION!_Setup.exe
    )
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ============================================================
echo   Build complete!  v!VERSION!
echo.
echo   Portable:   dist\%APPNAME%\HP_Analyzer.exe
if %DO_INSTALLER%==1 (
    echo   Installer:  release\HP_Analyzer_v!VERSION!_Setup.exe
)
echo ============================================================
echo.
pause

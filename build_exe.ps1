<#
.SYNOPSIS
    Builds the HP Semiconductor Analyzer Controller -- EXE and optional installer.

.DESCRIPTION
    1. Creates a Python virtual environment
    2. Installs all dependencies (PyQt5, PyVISA, matplotlib, numpy, ...)
    3. Bumps src/version.py from the latest git tag
    4. Runs PyInstaller  ->  dist\HP_Analyzer\HP_Analyzer.exe  (portable folder)
    5. [optional] Runs Inno Setup  ->  release\HP_Analyzer_v<ver>_Setup.exe
    6. [optional] Zips the portable folder for direct distribution

.PARAMETER Clean
    Delete build/, dist/, and the venv before starting.

.PARAMETER Installer
    Compile installer.iss with Inno Setup after PyInstaller.
    Inno Setup 6 must be installed: https://jrsoftware.org/isdl.php
    If ISCC.exe is not found the step is skipped with a warning.

.PARAMETER ZipOutput
    Also ZIP the dist\HP_Analyzer\ folder.

.EXAMPLE
    .\build_exe.ps1                          # portable folder only
    .\build_exe.ps1 -Installer               # portable folder + setup EXE
    .\build_exe.ps1 -Installer -ZipOutput    # both + ZIP
    .\build_exe.ps1 -Clean -Installer        # clean build + setup EXE
#>

param(
    [switch]$Clean,
    [switch]$Installer,
    [switch]$ZipOutput
)

# "Continue" lets native executables (pip, PyInstaller, ISCC) write to stderr
# without PS5.1 throwing a NativeCommandError and corrupting $LASTEXITCODE.
# Actual failures are detected via explicit $LASTEXITCODE checks below.
$ErrorActionPreference = "Continue"
$AppName  = "HP_Analyzer"
$VenvDir  = ".venv_build"

# -- Banner -------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  HP Semiconductor Analyzer Controller -- Build Script"         -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# -- 1. Locate Python 3.x -----------------------------------------------------
$PythonExe = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python 3\.") {
            $PythonExe = $candidate
            Write-Host "[OK] $ver" -ForegroundColor Green
            break
        }
    } catch { }
}
if (-not $PythonExe) {
    Write-Host "[ERROR] Python 3.8+ not found. Download from https://python.org" -ForegroundColor Red
    exit 1
}

# -- 2. Optional clean --------------------------------------------------------
if ($Clean) {
    Write-Host "[..] Cleaning previous build artefacts..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue "build", "dist", $VenvDir
    Write-Host "[OK] Clean complete." -ForegroundColor Green
}

# -- 3. Virtual environment ---------------------------------------------------
if (-not (Test-Path "$VenvDir\Scripts\python.exe")) {
    Write-Host "[..] Creating virtual environment in $VenvDir ..." -ForegroundColor Yellow
    & $PythonExe -m venv $VenvDir
    if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] venv creation failed." -ForegroundColor Red; exit 1 }
}
$Pip    = "$VenvDir\Scripts\pip.exe"
$Python = "$VenvDir\Scripts\python.exe"
Write-Host "[OK] Virtual environment ready." -ForegroundColor Green

# -- 4. Install dependencies --------------------------------------------------
Write-Host "[..] Installing / upgrading dependencies (first run may take ~5 min)..." -ForegroundColor Yellow
& $Pip install -r requirements.txt --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] requirements.txt install failed." -ForegroundColor Red; exit 1 }

& $Pip install pyinstaller pyinstaller-hooks-contrib openpyxl --quiet --disable-pip-version-check
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] PyInstaller install failed." -ForegroundColor Red; exit 1 }
Write-Host "[OK] Dependencies installed." -ForegroundColor Green

# -- 5. Generate version from git tag ----------------------------------------
Write-Host "[..] Reading version from git tag..." -ForegroundColor Yellow
& $Python scripts\gen_version.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[WARN] gen_version.py failed -- falling back to src/version.py" -ForegroundColor Yellow
}

# Read version string from the generated file (avoids PS5.1 string-parsing quirks)
$Version = "dev"
try {
    $vLine = Get-Content "src\version.py" -ErrorAction Stop |
        Where-Object { $_ -match '__version__' }
    if ($vLine -match '"([0-9][^"]+)"') { $Version = $Matches[1] }
} catch { }
Write-Host "[OK] Version: $Version" -ForegroundColor Green

# -- 6. Run PyInstaller -------------------------------------------------------
Write-Host ""
Write-Host "[..] Running PyInstaller (this takes 2-5 minutes)..." -ForegroundColor Yellow
& $Python -m PyInstaller hp_analyzer.spec --noconfirm
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] PyInstaller failed." -ForegroundColor Red; exit 1 }

$DistFolder = "dist\$AppName"
if (-not (Test-Path "$DistFolder\$AppName.exe")) {
    Write-Host "[ERROR] Expected EXE not found: $DistFolder\$AppName.exe" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] PyInstaller build complete  ->  $DistFolder\" -ForegroundColor Green

# -- 7. Inno Setup installer (optional) --------------------------------------
if ($Installer) {
    Write-Host ""
    Write-Host "[..] Looking for Inno Setup 6 (ISCC.exe)..." -ForegroundColor Yellow

    $ISCC = $null
    $candidates = @(
        "ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 7\ISCC.exe",
        "C:\Program Files\Inno Setup 7\ISCC.exe"
    )
    foreach ($c in $candidates) {
        try {
            if (Get-Command $c -ErrorAction SilentlyContinue) { $ISCC = $c; break }
            if (Test-Path $c) { $ISCC = $c; break }
        } catch { }
    }

    if (-not $ISCC) {
        Write-Host "[WARN] Inno Setup 6 (ISCC.exe) not found -- skipping installer step." -ForegroundColor Yellow
        Write-Host "       Download from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Found ISCC: $ISCC" -ForegroundColor Green
        if (-not (Test-Path "release")) { New-Item -ItemType Directory "release" | Out-Null }

        Write-Host "[..] Compiling installer.iss..." -ForegroundColor Yellow
        & $ISCC "installer.iss"
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] Inno Setup compilation failed." -ForegroundColor Red; exit 1
        }

        $SetupExe = "release\HP_Analyzer_v${Version}_Setup.exe"
        if (Test-Path $SetupExe) {
            $size = [math]::Round((Get-Item $SetupExe).Length / 1MB, 1)
            Write-Host "[OK] Installer ready  ->  $SetupExe  ($size MB)" -ForegroundColor Green
        } else {
            Write-Host "[WARN] Installer EXE not found at expected path: $SetupExe" -ForegroundColor Yellow
        }
    }
}

# -- 8. Optional ZIP of portable folder ---------------------------------------
if ($ZipOutput) {
    $ZipName = "${AppName}_v${Version}_Windows_Portable.zip"
    Write-Host "[..] Creating portable ZIP: $ZipName ..." -ForegroundColor Yellow
    if (Test-Path $ZipName) { Remove-Item $ZipName }
    Compress-Archive -Path "$DistFolder\*" -DestinationPath $ZipName
    $size = [math]::Round((Get-Item $ZipName).Length / 1MB, 1)
    Write-Host "[OK] Portable ZIP ready  ->  $ZipName  ($size MB)" -ForegroundColor Green
}

# -- Done ---------------------------------------------------------------------
Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Build complete!  v$Version"                                    -ForegroundColor Cyan
Write-Host ""
Write-Host "  Portable folder:  dist\HP_Analyzer\HP_Analyzer.exe"           -ForegroundColor White
if ($Installer) {
    $SetupExe = "release\HP_Analyzer_v${Version}_Setup.exe"
    if (Test-Path $SetupExe) {
        Write-Host "  Installer EXE:    $SetupExe"                           -ForegroundColor White
    }
}
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

@echo off
setlocal

echo.
echo ========================================
echo    AquaVision Installer (Windows)
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: python not found. Install Python 3.10+ from https://python.org and try again.
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate.bat

echo [2/5] Installing PyTorch (CPU)...
pip install --quiet --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

echo [3/5] Installing dependencies...
pip install --quiet --no-cache-dir -r requirements.txt

echo [4/5] Installing SAM v1...
pip install --quiet --no-cache-dir "git+https://github.com/facebookresearch/segment-anything.git"

echo [5/5] Installing SAM2 and DEXTR...
pip install --quiet --no-cache-dir vendor\sam2
pip install --quiet --no-cache-dir vendor\DEXTR

echo.
echo ========================================
echo    Installation complete!
echo    Run run.bat to start AquaVision.
echo ========================================
echo.
pause

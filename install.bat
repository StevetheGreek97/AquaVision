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

echo [5/6] Installing SAM2 and DEXTR...
pip install --quiet --no-cache-dir "git+https://github.com/facebookresearch/sam2.git"
git clone --quiet "https://github.com/StevetheGreek97/DEXTR-SMe.git" "%TEMP%\dextr_sme"
type nul > "%TEMP%\dextr_sme\src\DEXTR\__init__.py"
pip install --quiet --no-cache-dir "%TEMP%\dextr_sme"
rmdir /s /q "%TEMP%\dextr_sme"

echo [6/6] Setting up SAM2 configs and downloading model...
if not exist "sam2_configs" mkdir sam2_configs

python -c "import sam2, os, shutil; src=os.path.join(os.path.dirname(sam2.__file__),'configs','sam2'); [shutil.copy2(os.path.join(src,f),'sam2_configs/'+f) for f in os.listdir(src) if f.endswith('.yaml')]; print('  Configs copied.')"

if not exist "sam2_configs\sam2_hiera_tiny.pt" (
    echo   Downloading sam2_hiera_tiny.pt ~155 MB...
    curl -L --progress-bar "https://dl.fbaipublicfiles.com/segment_anything_2/072824/sam2_hiera_tiny.pt" -o "sam2_configs\sam2_hiera_tiny.pt"
) else (
    echo   sam2_hiera_tiny.pt already present, skipping.
)

echo.
echo ========================================
echo    Installation complete!
echo    Run run.bat to start AquaVision.
echo ========================================
echo.
pause

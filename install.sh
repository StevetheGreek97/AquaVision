#!/bin/bash
set -e

# Always resolve paths relative to this script, regardless of where it's called from
cd "$(dirname "$0")"

echo ""
echo "========================================"
echo "   SegmentME Installer (Linux / macOS)"
echo "========================================"
echo ""

# Check Python 3.10+
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Install Python 3.10 or newer and try again."
    exit 1
fi

PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    echo "ERROR: Python 3.10+ required (found $PY_VER)."
    exit 1
fi

echo "Python $PY_VER detected."
echo ""

# Create virtual environment
echo "[1/5] Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# PyTorch CPU-only
echo "[2/5] Installing PyTorch (CPU)..."
pip install --quiet --no-cache-dir \
    torch torchvision \
    --index-url https://download.pytorch.org/whl/cpu

# Main requirements
echo "[3/5] Installing dependencies..."
pip install --quiet --no-cache-dir -r requirements.txt

# SAM v1
echo "[4/5] Installing SAM v1..."
pip install --quiet --no-cache-dir \
    "git+https://github.com/facebookresearch/segment-anything.git"

# SAM2 and DEXTR
echo "[5/5] Installing SAM2 and DEXTR..."
pip install --quiet --no-cache-dir "git+https://github.com/facebookresearch/sam2.git"
pip install --quiet --no-cache-dir "git+https://github.com/StevetheGreek97/DEXTR-SMe.git"

echo ""
echo "========================================"
echo "   Installation complete!"
echo "   Run ./run.sh to start AquaVision."
echo "========================================"
echo ""

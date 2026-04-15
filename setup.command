#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo " ========================================"
echo "  Sachalayatan Downloader — Setup"
echo " ========================================"
echo ""

# ── Check Python ───────────────────────────────────────────────────────────────
echo " Checking Python..."

if command -v python3 &>/dev/null; then
    PYVER=$(python3 --version)
    echo " Found: $PYVER"
elif command -v python &>/dev/null; then
    PYVER=$(python --version)
    echo " Found: $PYVER"
else
    echo ""
    echo " [ERROR] Python is not installed."
    echo ""
    echo " Please do the following:"
    echo "   1. Go to https://www.python.org/downloads/"
    echo "   2. Click Download Python and run the installer"
    echo "   3. Re-run this setup file"
    echo ""
    read -p " Press Enter to close..."
    exit 1
fi

echo ""

# ── Install packages ───────────────────────────────────────────────────────────
echo " Installing required packages..."
echo " (this may take a minute)"
echo ""

if command -v python3 &>/dev/null; then
    python3 -m pip install --upgrade pip --quiet
    python3 -m pip install requests beautifulsoup4 lxml flask --quiet
else
    python -m pip install --upgrade pip --quiet
    python -m pip install requests beautifulsoup4 lxml flask --quiet
fi

if [ $? -ne 0 ]; then
    echo ""
    echo " [ERROR] Package installation failed."
    echo " Try running this command manually:"
    echo ""
    echo "     pip3 install requests beautifulsoup4 lxml flask"
    echo ""
    read -p " Press Enter to close..."
    exit 1
fi

# ── Make start.command executable ─────────────────────────────────────────────
if [ -f "start.command" ]; then
    chmod +x start.command
fi

echo ""
echo " ========================================"
echo "  Setup complete!"
echo " ========================================"
echo ""
echo " To start the app, double-click start.command"
echo ""
read -p " Press Enter to close..."

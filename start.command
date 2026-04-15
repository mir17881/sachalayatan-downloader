#!/bin/bash
cd "$(dirname "$0")"

echo ""
echo " ========================================"
echo "  Sachalayatan Downloader"
echo " ========================================"
echo ""
echo " Starting... your browser will open soon."
echo " Keep this window open while using the app."
echo " To stop: close this window or press Ctrl+C."
echo ""

python3 app.py

echo ""
echo " The app has stopped."
if [ $? -ne 0 ]; then
    echo ""
    echo " Something went wrong. Make sure you have installed"
    echo " the required packages by running:"
    echo ""
    echo "     pip3 install requests beautifulsoup4 lxml flask"
    echo ""
fi

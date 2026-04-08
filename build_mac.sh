#!/bin/bash
echo "Packaging SupaMap Executable for macOS..."
echo "Installing PyInstaller explicitly..."
pip install pyinstaller

echo "Booting Pyinstaller with Bundled Assets..."
pyinstaller --noconfirm --onedir --windowed \
--add-data "assets:assets" \
--collect-data folium \
--name "SupaMap" \
main.py

echo ""
echo "========================================================"
echo "BUILD COMPLETE!"
echo "Your SupaMap macOS Application is located exactly at:"
echo "dist/SupaMap.app"
echo "========================================================"

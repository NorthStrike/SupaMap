@echo off
echo Packaging SupaMap Executable...
echo Installing PyInstaller explicitly...
call .\venv\Scripts\pip.exe install pyinstaller

echo Booting Pyinstaller with Bundled Assets...
call .\venv\Scripts\pyinstaller.exe --noconfirm --onedir --windowed ^
--add-data "assets;assets" ^
--collect-data folium ^
--name "SupaMap" ^
main.py

echo.
echo ========================================================
echo BUILD COMPLETE!
echo Your SupaMap executable is located exactly at:
echo dist\SupaMap\SupaMap.exe
echo ========================================================
pause

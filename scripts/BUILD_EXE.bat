@echo off
setlocal
cd /d "%~dp0\.."
echo === BANNARAKX UNIFIED - build ===
where py >nul 2>nul || (echo Python 3.12 not found. Install from python.org & pause & exit /b 1)
if not exist .venv ( py -3.12 -m venv .venv || py -3 -m venv .venv )
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements-dev.txt || (echo pip failed & pause & exit /b 1)
python -m pytest -q tests || (echo TESTS FAILED - build stopped & pause & exit /b 1)
rem (manifest is verified by the tests)
pyinstaller --noconfirm --clean --onefile --windowed --uac-admin ^
  --name BANNARAKX_UNIFIED --icon assets\logo.ico ^
  --add-data "assets;assets" ^
  --distpath dist\BANNARAKX_UNIFIED --workpath build run.py || (echo BUILD FAILED & pause & exit /b 1)
xcopy /E /I /Y originals dist\BANNARAKX_UNIFIED\originals >nul
echo.
echo DONE:  dist\BANNARAKX_UNIFIED\BANNARAKX_UNIFIED.exe
echo Keep the "originals" folder next to the exe.
pause

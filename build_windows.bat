@echo off
setlocal
cd /d %~dp0
py -m pip install --upgrade pip
py -m pip install -r requirements.txt pyinstaller
if errorlevel 1 exit /b 1
py -m unittest discover -s tests -v
if errorlevel 1 exit /b 1
py -m PyInstaller --noconfirm --clean --onefile --windowed --name ChiffresClesMartinique launch_app.py
if errorlevel 1 exit /b 1
copy /Y dist\ChiffresClesMartinique.exe .\ChiffresClesMartinique.exe
echo.
echo Build termine : %CD%\ChiffresClesMartinique.exe
endlocal

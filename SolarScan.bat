@echo off
rem SolarScan desktop interface. Double-click to start.
rem First run: installs SolarScan and its dependencies (needs internet once).
setlocal
cd /d "%~dp0"

rem Find Python: the "py" launcher first, then "python" on PATH.
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
    echo Python 3.10 or newer is needed: https://www.python.org/downloads/
    echo Tick "Add python.exe to PATH" during installation, then run this file again.
    pause
    exit /b 1
)

rem Install on first run (or after the package was removed).
%PY% -c "import solarscan.gui, shapely, pyproj, reportlab, matplotlib, PIL" >nul 2>&1
if errorlevel 1 (
    echo Installing SolarScan for the first time. This takes a minute...
    %PY% -m pip install --quiet -e . pillow
    if errorlevel 1 (
        echo Installation failed. See the messages above.
        pause
        exit /b 1
    )
)

rem Start the window without keeping this console open (pythonw has no console).
for /f "delims=" %%i in ('%PY% -c "import sys, os; print(os.path.join(os.path.dirname(sys.executable), 'pythonw.exe'))"') do set "PYW=%%i"
if exist "%PYW%" (
    start "" "%PYW%" -m solarscan.gui
) else (
    %PY% -m solarscan.gui
)
endlocal

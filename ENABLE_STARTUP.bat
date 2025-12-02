@echo off
REM Create a startup shortcut for Kayas Background Service
REM This will make Kayas start automatically when Windows boots

echo ========================================
echo Kayas Startup Configuration
echo ========================================
echo.

set STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
set SCRIPT_PATH=%~dp0START_KAYAS_BACKGROUND.bat

echo Creating startup shortcut...
echo.
echo Target: %SCRIPT_PATH%
echo Startup folder: %STARTUP_FOLDER%
echo.

REM Create a VBS script to create the shortcut
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%STARTUP_FOLDER%\Kayas Background.lnk" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%SCRIPT_PATH%" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%~dp0" >> CreateShortcut.vbs
echo oLink.Description = "Kayas AI Assistant - Background Service" >> CreateShortcut.vbs
echo oLink.WindowStyle = 7 >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

cscript //nologo CreateShortcut.vbs
del CreateShortcut.vbs

echo.
echo ✅ Startup shortcut created!
echo.
echo Kayas will now start automatically when Windows boots.
echo The service runs minimized in the background.
echo.
echo To disable auto-start:
echo 1. Press Win+R
echo 2. Type: shell:startup
echo 3. Delete "Kayas Background.lnk"
echo.

pause

@echo off
REM Copy the per-suite sweep logs out of %TEMP% into logs\sweep so the file
REM bridge can read them. Written 2026-08-22.
setlocal
cd /d "%~dp0"
if not exist "logs\sweep" mkdir "logs\sweep"
xcopy /Y /I "%TEMP%\covenant_sweep\logs\*.log" "logs\sweep\" > NUL
dir /b "logs\sweep"
echo copied
pause
endlocal

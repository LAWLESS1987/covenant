@echo off
REM COVENANT_CHAT.bat -- one double-click to talk to the covenant on its own
REM local judge. Nothing leaves this machine. First reply takes ~30-90 s while
REM the judge loads; !help inside for commands; !quit or close the window to end.
title COVENANT -- chat
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
"%PY%" covenant_chat.py
echo.
pause
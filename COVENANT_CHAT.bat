@echo off
REM COVENANT_CHAT.bat -- one double-click to talk to the covenant.
REM
REM This said "on its own local judge. Nothing leaves this machine." until
REM 2026-09-11. Ollama was deleted from this PC on 2026-09-07, so there is no
REM local judge: every turn goes to a GitHub Actions runner and LEAVES THIS PC,
REM into a workflow_dispatch input on a PUBLIC repository. The chat's opening
REM banner probes and says so; !github off stops it (and then nothing answers).
REM MEMORY and the live state are withheld from what is sent; the conversation
REM is not. See the header of covenant_chat.py.
REM
REM !help inside for commands; !quit or close the window to end.
title COVENANT -- chat
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
"%PY%" covenant_chat.py
echo.
pause
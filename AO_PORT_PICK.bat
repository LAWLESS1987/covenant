@echo off
REM ===========================================================================
REM  AO_PORT_PICK.bat -- which port blocks can a node actually BIND?
REM
REM  netstat shows what is listening. It does NOT show Windows' reserved and
REM  excluded port ranges, which fail a bind with WinError 10013 and are
REM  invisible until a node dies at startup. This binds, which is the only
REM  question that matters.
REM
REM  Writes PORT_PICK.txt.
REM ===========================================================================
setlocal
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo.
echo   Bind-probing 5000-5400 for blocks of three. A moment ...
echo.
"%PY%" pick_node_ports.py 5000 5400 > PORT_PICK.txt 2>&1
type PORT_PICK.txt
echo.
echo   Written to PORT_PICK.txt
echo.
pause
endlocal

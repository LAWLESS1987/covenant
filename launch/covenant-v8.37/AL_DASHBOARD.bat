@echo off
REM ==================================================================
REM  AL_DASHBOARD.bat -- the 3D view of the mesh.
REM
REM  Double-click it. It asks both nodes what state they are in, writes
REM  dashboard.html, opens it in your browser, then keeps rewriting it
REM  every 20 seconds. The page reloads itself and keeps your camera
REM  angle, so it stays live without you touching anything.
REM
REM  Close THIS window to stop refreshing. The page stays open and its
REM  age badge goes amber then red, so a stopped refresher can never
REM  masquerade as a calm system.
REM
REM  The page never talks to the network itself. All the data is baked
REM  into the file, which is why it still renders when a node is DOWN
REM  -- and that is exactly when you want to look at it.
REM ==================================================================
title COVENANT DASHBOARD
cd /d "%~dp0"

set PY=.venv\Scripts\python.exe
if exist "%PY%" goto HAVEPY
set PY=python
:HAVEPY

if exist "vendor\three.min.js" goto HAVE3D
echo.
echo   vendor\three.min.js is missing -- the page would be blank.
echo   Nothing here can fix that; the file has to be put back.
echo.
pause
exit /b 1
:HAVE3D

echo.
echo   Reading node A on 5000 and node B on 5020 ...
echo.
"%PY%" dashboard_render.py --open --watch 20

echo.
echo   Refresher stopped. The open page is now a snapshot and will say so.
pause

@echo off
REM  covenant_diag.bat -- read-only. Why is the anchor taking so long?
setlocal
cd /d "%~dp0"
set R=diag_out.txt
echo === diag %DATE% %TIME% === > %R%

echo -- ollama reachable? -- >> %R%
curl -s -m 8 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (echo   NO - ollama is down >> %R%) else (echo   yes >> %R%)
echo -- models loaded right now (blank = model unloaded, must reload) -- >> %R%
ollama ps >> %R% 2>&1
echo -- installed -- >> %R%
ollama list >> %R% 2>&1

echo. >> %R%
echo -- node A health -- >> %R%
curl -s -m 10 http://127.0.0.1:5000/health >> %R% 2>&1
echo. >> %R%
echo -- node B health -- >> %R%
curl -s -m 10 http://127.0.0.1:5020/health >> %R% 2>&1
echo. >> %R%

echo -- free memory (KB) -- >> %R%
wmic OS get FreePhysicalMemory /format:list 2>nul | findstr /r "." >> %R%
echo -- python processes -- >> %R%
tasklist /fi "imagename eq python.exe" >> %R% 2>&1
echo -- ollama processes -- >> %R%
tasklist /fi "imagename eq ollama.exe" >> %R% 2>&1

type %R%
echo.
echo Wrote diag_out.txt
pause
endlocal

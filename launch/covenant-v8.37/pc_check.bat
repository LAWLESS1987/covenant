@echo off
REM ============================================================
REM  pc_check.bat -- read-only. Writes pc_report.txt and changes
REM  NOTHING on this machine. Double-click it, then tell Claude.
REM ============================================================
cd /d "%~dp0"
set R=pc_report.txt
echo Covenant PC report > %R%
echo generated %DATE% %TIME% >> %R%
echo. >> %R%

echo == CPU == >> %R%
wmic cpu get Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed /format:list 2>nul | findstr /r "." >> %R%
echo. >> %R%

echo == MEMORY (bytes) == >> %R%
wmic computersystem get TotalPhysicalMemory /format:list 2>nul | findstr /r "." >> %R%
wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /format:list 2>nul | findstr /r "." >> %R%
echo. >> %R%

echo == GPU == >> %R%
wmic path win32_VideoController get Name,AdapterRAM,DriverVersion /format:list 2>nul | findstr /r "." >> %R%
echo -- nvidia-smi -- >> %R%
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv 2>>%R% >>%R%
echo. >> %R%

echo == DISK == >> %R%
wmic logicaldisk where "DeviceID='C:'" get Size,FreeSpace /format:list 2>nul | findstr /r "." >> %R%
echo. >> %R%

echo == POWER PLAN == >> %R%
powercfg /getactivescheme >> %R% 2>&1
echo. >> %R%

echo == OLLAMA == >> %R%
ollama --version >> %R% 2>&1
echo -- models -- >> %R%
ollama list >> %R% 2>&1
echo -- loaded right now -- >> %R%
ollama ps >> %R% 2>&1
echo -- OLLAMA_* environment -- >> %R%
set OLLAMA >> %R% 2>&1
echo -- what 11434 is bound to (0.0.0.0 = exposed to your LAN) -- >> %R%
netstat -ano ^| findstr :11434 >> %R% 2>&1
echo. >> %R%

echo == PYTHON == >> %R%
python --version >> %R% 2>&1
if exist ".venv\Scripts\python.exe" (.venv\Scripts\python.exe --version >> %R% 2>&1) else (echo no .venv >> %R%)
echo. >> %R%

echo == COVENANT STATE == >> %R%
if exist nodeA_prod.db (echo nodeA_prod.db PRESENT >> %R%) else (echo nodeA_prod.db absent - never launched >> %R%)
if exist live_out.txt (echo live_out.txt PRESENT >> %R%) else (echo live_out.txt absent >> %R%)
if exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" (echo founder key backup PRESENT >> %R%) else (echo founder key backup MISSING >> %R%)
echo. >> %R%

type %R%
echo.
echo ============================================================
echo Wrote pc_report.txt in this folder. Tell Claude "report ready".
echo Nothing on this machine was changed.
echo ============================================================
pause

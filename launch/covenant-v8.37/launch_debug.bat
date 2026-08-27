@echo off
REM Logs EVERYTHING to launch_log.txt so Claude can see what happened.
cd /d "%~dp0"
set LOG=launch_log.txt
echo ==== LAUNCH LOG %DATE% %TIME% ==== > %LOG%

echo [1] folder: %cd% >> %LOG% 2>&1
echo [2] activating venv... >> %LOG% 2>&1
call ".venv\Scripts\activate.bat" >> %LOG% 2>&1
echo     activate errorlevel=%errorlevel% >> %LOG% 2>&1

echo [3] python version: >> %LOG% 2>&1
python --version >> %LOG% 2>&1
echo     errorlevel=%errorlevel% >> %LOG% 2>&1

echo [4] required imports: >> %LOG% 2>&1
python -c "import flask,cryptography,requests;print('deps OK')" >> %LOG% 2>&1
echo     errorlevel=%errorlevel% >> %LOG% 2>&1

echo [5] core module import: >> %LOG% 2>&1
python -c "import covenant_unified_v8 as c;print('core OK',c.COVENANT_VERSION)" >> %LOG% 2>&1
echo     errorlevel=%errorlevel% >> %LOG% 2>&1

echo [6] judge wrapper import: >> %LOG% 2>&1
python -c "import run_with_claude_judge;print('judge wrapper OK')" >> %LOG% 2>&1
echo     errorlevel=%errorlevel% >> %LOG% 2>&1

echo [7] copying founder key... >> %LOG% 2>&1
if exist nodeA_prod.db del /q nodeA_prod.db >> %LOG% 2>&1
if exist nodeB_prod.db del /q nodeB_prod.db >> %LOG% 2>&1
copy /y covenant_A.db.key nodeA_prod.db.key >> %LOG% 2>&1
echo     errorlevel=%errorlevel% >> %LOG% 2>&1

echo [8] starting node A on 5000 (background, log nodeA.log)... >> %LOG% 2>&1
set COVENANT_JUDGE_TIMEOUT=300
set COVENANT_DB_PATH=nodeA_prod.db
start "Covenant Node A" /min cmd /c "set COVENANT_JUDGE_TIMEOUT=300&& set COVENANT_DB_PATH=nodeA_prod.db&& python run_with_claude_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021 > nodeA.log 2>&1"

echo [9] starting node B on 5020 (background, log nodeB.log)... >> %LOG% 2>&1
start "Covenant Node B" /min cmd /c "set COVENANT_JUDGE_TIMEOUT=300&& set COVENANT_DB_PATH=nodeB_prod.db&& python run_with_claude_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001 > nodeB.log 2>&1"

echo [10] waiting 20s for startup... >> %LOG% 2>&1
timeout /t 20 /nobreak > nul

echo [11] node status: >> %LOG% 2>&1
python covenant_client.py status --ports 5000,5020 >> %LOG% 2>&1
echo     errorlevel=%errorlevel% >> %LOG% 2>&1

echo [12] node A log tail: >> %LOG% 2>&1
if exist nodeA.log (type nodeA.log >> %LOG% 2>&1) else (echo     nodeA.log missing >> %LOG% 2>&1)

echo ==== END ==== >> %LOG% 2>&1
echo.
echo Done. Everything was written to launch_log.txt
echo Tell Claude "done" and it will read the log.
echo.
type launch_log.txt
pause

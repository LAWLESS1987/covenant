@echo off
REM ============================================================
REM  Covenant LIVE with CLAUDE as the ethics gate (no API key)
REM  Each transaction waits for Claude's verdict, written to
REM  judge_queue\verdicts through the connected folder.
REM  Run in a terminal:  start_live_claude.bat
REM ============================================================
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM how long a node waits for Claude's verdict before failing CLOSED
set COVENANT_JUDGE_TIMEOUT=300

if not exist "genesis.json" ( echo genesis.json missing - run run_setup.bat first. & pause & exit /b 1 )
if not exist "covenant_A.db.key" ( echo covenant_A.db.key missing - run run_setup.bat first. & pause & exit /b 1 )
if not exist "run_with_claude_judge.py" ( echo run_with_claude_judge.py missing. & pause & exit /b 1 )

REM fresh production dbs; founder key -> node A so it holds the genesis 1000
for %%F in (nodeA_prod.db nodeA_prod.db-wal nodeA_prod.db-shm nodeB_prod.db nodeB_prod.db-wal nodeB_prod.db-shm) do if exist "%%F" del /q "%%F"
copy /y covenant_A.db.key nodeA_prod.db.key >nul
if not exist "judge_queue" mkdir judge_queue
if not exist "judge_queue\requests" mkdir judge_queue\requests
if not exist "judge_queue\verdicts" mkdir judge_queue\verdicts

echo Starting node A (port 5000, Claude-judged)...
start "Covenant Node A (Claude-judged)" cmd /k "set COVENANT_JUDGE_TIMEOUT=300&& set COVENANT_DB_PATH=nodeA_prod.db&& python run_with_claude_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021"
echo Starting node B (port 5020, Claude-judged)...
start "Covenant Node B (Claude-judged)" cmd /k "set COVENANT_JUDGE_TIMEOUT=300&& set COVENANT_DB_PATH=nodeB_prod.db&& python run_with_claude_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001"

echo Waiting ~14s for both nodes to come up and peer...
timeout /t 14 /nobreak >nul

python covenant_client.py status --ports 5000,5020 > live_claude_out.txt 2>&1
echo ============================================================
type live_claude_out.txt
echo ============================================================
echo.
echo Your ledger is LIVE, with CLAUDE as the ethics gate. No API key.
echo.
echo To make a transaction: tell Claude what you want to send. Claude writes a
echo verdict into judge_queue\verdicts, then you run, e.g.:
echo   python covenant_client.py --port 5000 --key nodeA_prod.db.key send --to-key nodeB_prod.db.key --amount 25
echo   python covenant_client.py --port 5000 --key nodeA_prod.db.key mine
echo.
echo The two node windows are your live network; close them to stop.
pause
endlocal

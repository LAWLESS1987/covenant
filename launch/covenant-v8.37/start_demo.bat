@echo off
REM ============================================================
REM  Covenant LIVE DEMO (dev mode / mock judge -- no API key needed)
REM  Brings up two nodes, runs a real transaction, shows them sync.
REM  Reuses the genesis + founder key you already created.
REM  Run in a terminal:  start_demo.bat
REM ============================================================
setlocal
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM dev mode: keyword judge so transactions flow without an API key
set COVENANT_JUDGE_PROVIDERS=mock
set COVENANT_INSECURE_MOCK_JUDGE=1

if not exist "genesis.json" (
  echo genesis.json not found -- run run_setup.bat first.
  pause & exit /b 1
)
if not exist "covenant_A.db.key" (
  echo covenant_A.db.key not found -- run run_setup.bat first.
  pause & exit /b 1
)

REM fresh run databases so we never touch your setup files; the founder key
REM (covenant_A.db.key) is copied in so node A holds the genesis 1000.
for %%F in (nodeA_run.db nodeA_run.db-wal nodeA_run.db-shm nodeB_run.db nodeB_run.db-wal nodeB_run.db-shm) do if exist "%%F" del /q "%%F"
copy /y covenant_A.db.key nodeA_run.db.key >nul

echo Starting node A (port 5000) in its own window...
start "Covenant Node A" cmd /k "set COVENANT_JUDGE_PROVIDERS=mock&& set COVENANT_INSECURE_MOCK_JUDGE=1&& set COVENANT_DB_PATH=nodeA_run.db&& python covenant_unified_v8.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021"

echo Starting node B (port 5020) in its own window...
start "Covenant Node B" cmd /k "set COVENANT_JUDGE_PROVIDERS=mock&& set COVENANT_INSECURE_MOCK_JUDGE=1&& set COVENANT_DB_PATH=nodeB_run.db&& python covenant_unified_v8.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001"

echo Waiting ~14s for both nodes to come up and find each other...
timeout /t 14 /nobreak >nul

echo.
echo == founder balance (expect 1000) ==
python covenant_client.py balance --db nodeA_run.db --of-key nodeA_run.db.key
echo.
echo == send 25 from A to B ==
python covenant_client.py --port 5000 --key nodeA_run.db.key send --to-key nodeB_run.db.key --amount 25
echo.
echo == mine the block on A ==
python covenant_client.py --port 5000 --key nodeA_run.db.key mine
timeout /t 6 /nobreak >nul
echo.
echo == network status (expect converged: True) ==
python covenant_client.py status --ports 5000,5020
echo.
echo == balances after (expect A 975, B 25) ==
python covenant_client.py balance --db nodeA_run.db --of-key nodeA_run.db.key
python covenant_client.py balance --db nodeA_run.db --of-key nodeB_run.db.key
echo.
echo Your ledger is LIVE. Nodes A and B are running in their own windows.
echo Close those two windows to stop the network.
pause
endlocal

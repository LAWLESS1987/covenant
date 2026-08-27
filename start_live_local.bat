@echo off
REM ============================================================
REM  Covenant PRODUCTION launch -- LOCAL judge (Ollama), NO API key.
REM
REM  The ethics gate is qwen3.6 running on your own machine. No key,
REM  no bill, no internet, and the insecure keyword mock is OFF.
REM
REM  Requires run_with_local_judge.py in this folder -- the node cannot
REM  load the "local" provider without it. See that file's docstring.
REM
REM  Run in a terminal:  start_live_local.bat
REM ============================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM -- the local judge wiring (OLLAMA_JUDGE.md section 2) ----------------
set COVENANT_LOCAL_JUDGE_URL=http://localhost:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3.6:latest
REM A judge TIMEOUT is recorded as a VIOLATION. Your model is ~22GB, so on
REM CPU one verdict can take minutes. Do not lower these.
set COVENANT_LOCAL_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_PROVIDERS=local
REM never fall back to keyword matching
set "COVENANT_INSECURE_MOCK_JUDGE="

echo.
echo === Covenant PRODUCTION launch -- local judge, no API key ===
echo.

if not exist "run_with_local_judge.py" (
  echo run_with_local_judge.py is missing from this folder.
  echo Without it the node dies with: unknown judge provider: 'local'
  pause & exit /b 1
)

echo Checking Ollama is up on 11434 ...
curl -s -m 8 http://localhost:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  echo.
  echo Ollama is not answering on localhost:11434.
  echo Start it ^(launch the Ollama app, or run: ollama serve^) and try again.
  echo A judge that cannot be reached fails CLOSED - every transaction is rejected.
  pause & exit /b 1
)
echo   Ollama is up.

echo.
echo === Judge sanity check (benign transaction + an outright theft) ===
echo This loads a 22GB model. The FIRST verdict can take several minutes.
echo.
python judge_check.py
echo.
echo Read the verdict above before continuing.
echo   WORKING             -^> good, carry on.
echo   Approves EVERYTHING -^> stop. That is worse than no gate.
echo   Blocks EVERYTHING   -^> stop. The model is not returning parseable JSON.
echo.
choice /c YN /m "Did it say WORKING - continue with the launch"
if errorlevel 2 ( echo Stopped. & pause & exit /b 1 )

if not exist "genesis.json" ( echo genesis.json missing - run run_setup.bat first. & pause & exit /b 1 )
if not exist "covenant_A.db.key" ( echo covenant_A.db.key missing - run run_setup.bat first. & pause & exit /b 1 )

REM --- BACK UP THE FOUNDER KEY FIRST --------------------------------
REM covenant_A.db.key is the founder identity AND the genesis mint key.
REM run_all_tests.sh deletes *.db.key in this folder. Back it up.
if not exist "%USERPROFILE%\.covenant-keys" mkdir "%USERPROFILE%\.covenant-keys" >nul 2>nul
if not exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" (
  copy /y covenant_A.db.key "%USERPROFILE%\.covenant-keys\covenant_A.db.key" >nul
  echo Founder key backed up to %USERPROFILE%\.covenant-keys\
)

REM --- fresh PRODUCTION databases -----------------------------------
REM Explicit filenames on purpose: a wildcard like nodeA_prod.db* would also
REM delete nodeA_prod.db.key, which is your founder identity.
if exist "nodeA_prod.db"     del /q "nodeA_prod.db"
if exist "nodeA_prod.db-wal" del /q "nodeA_prod.db-wal"
if exist "nodeA_prod.db-shm" del /q "nodeA_prod.db-shm"
if exist "nodeB_prod.db"     del /q "nodeB_prod.db"
if exist "nodeB_prod.db-wal" del /q "nodeB_prod.db-wal"
if exist "nodeB_prod.db-shm" del /q "nodeB_prod.db-shm"
copy /y covenant_A.db.key nodeA_prod.db.key >nul

echo.
echo Starting node A (port 5000, LIVE, local judge)...
start "Covenant Node A (LIVE local)" cmd /k "set COVENANT_DB_PATH=nodeA_prod.db&& set COVENANT_LOCAL_JUDGE_URL=%COVENANT_LOCAL_JUDGE_URL%&& set COVENANT_LOCAL_JUDGE_MODEL=%COVENANT_LOCAL_JUDGE_MODEL%&& set COVENANT_LOCAL_JUDGE_TIMEOUT=300&& set COVENANT_JUDGE_TIMEOUT=300&& python run_with_local_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021"
echo Starting node B (port 5020, LIVE, local judge)...
start "Covenant Node B (LIVE local)" cmd /k "set COVENANT_DB_PATH=nodeB_prod.db&& set COVENANT_LOCAL_JUDGE_URL=%COVENANT_LOCAL_JUDGE_URL%&& set COVENANT_LOCAL_JUDGE_MODEL=%COVENANT_LOCAL_JUDGE_MODEL%&& set COVENANT_LOCAL_JUDGE_TIMEOUT=300&& set COVENANT_JUDGE_TIMEOUT=300&& python run_with_local_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001"

echo Waiting ~20s for nodes to come up and peer...
timeout /t 20 /nobreak >nul

echo == LIVE run through the LOCAL ethics gate == > live_out.txt
echo -- judge in use -->> live_out.txt
curl -s -m 8 http://127.0.0.1:5000/health >> live_out.txt 2>&1
echo. >> live_out.txt
echo -- founder balance (expect 1000) -->> live_out.txt
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
echo -- send 10 A-^>B (the local model judges this; may take minutes) -->> live_out.txt
python covenant_client.py --port 5000 --key nodeA_prod.db.key send --to-key nodeB_prod.db.key --amount 10 >> live_out.txt 2>&1
echo -- mine -->> live_out.txt
python covenant_client.py --port 5000 --key nodeA_prod.db.key mine >> live_out.txt 2>&1
timeout /t 8 /nobreak >nul
echo -- status (expect converged True) -->> live_out.txt
python covenant_client.py status --ports 5000,5020 >> live_out.txt 2>&1
echo -- balances on BOTH dbs (they MUST agree) -->> live_out.txt
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
python covenant_client.py balance --db nodeB_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
python covenant_client.py balance --db nodeA_prod.db --of-key nodeB_prod.db.key >> live_out.txt 2>&1
python covenant_client.py balance --db nodeB_prod.db --of-key nodeB_prod.db.key >> live_out.txt 2>&1

echo.
echo ============================================================
type live_out.txt
echo ============================================================
echo.
echo Expect: founder 1000 -^> 990, nodeB 10, converged True, and the
echo         founder/nodeB balances IDENTICAL across both dbs.
echo Saved to live_out.txt. Tell Claude "done" and it will read it.
pause
endlocal

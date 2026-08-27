@echo off
REM ============================================================================
REM  start_live_ollama.bat -- PRODUCTION launch behind the tuned local judge.
REM
REM  Same sequence as start_live_local.bat, with three changes:
REM    * imports covenant_judge_ollama, which re-registers provider "local"
REM      as the tuned /api/chat judge (thinking off, constrained JSON,
REM      deterministic, model pinned resident).
REM    * runs judge_bench.py, six cases, instead of judge_check.py's two --
REM      including the metadata-only payload that covenant_client.py send
REM      actually produces, which the two-case check never exercises.
REM    * checks Ollama is bound to loopback before starting anything.
REM
REM  Run in a terminal:  start_live_ollama.bat
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

REM -- judge wiring -----------------------------------------------------------
set COVENANT_LOCAL_JUDGE_URL=http://127.0.0.1:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b
REM A judge TIMEOUT is recorded as a VIOLATION. Generous on purpose.
set COVENANT_LOCAL_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_TIMEOUT=300
set COVENANT_JUDGE_PROVIDERS=local
REM never fall back to keyword matching
set "COVENANT_INSECURE_MOCK_JUDGE="
REM -- tuned per-request options (override any of these here) ------------------
set COVENANT_OLLAMA_NUM_PREDICT=160
set COVENANT_OLLAMA_NUM_CTX=2048
set COVENANT_OLLAMA_KEEP_ALIVE=30m

echo.
echo === Covenant PRODUCTION launch -- tuned local judge, no API key ===
echo.

if not exist "covenant_judge_ollama.py" (
  echo covenant_judge_ollama.py is missing. Without it you get the untuned
  echo path: minutes per verdict instead of seconds.
  pause & exit /b 1
)
if not exist "run_with_ollama_judge.py" (
  echo run_with_ollama_judge.py is missing from this folder.
  echo Without it the node dies with: unknown judge provider: 'local'
  pause & exit /b 1
)

echo Checking Ollama is up on 11434 ...
curl -s -m 8 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  echo.
  echo Ollama is not answering on 127.0.0.1:11434.
  echo Start it ^(the Ollama app, or: ollama serve^) and try again.
  echo A judge that cannot be reached fails CLOSED - every transaction rejected.
  pause & exit /b 1
)
echo   Ollama is up.

echo Checking it is not exposed to the network ...
netstat -ano | findstr ":11434" | findstr "0.0.0.0 \[::\]" >nul 2>nul
if %errorlevel% equ 0 (
  echo.
  echo   WARNING: Ollama is listening on 0.0.0.0, not loopback. It has no
  echo   authentication, so anything that can reach this machine can load
  echo   models, run inference, and see prompts. Run ollama_tune.bat, or set
  echo   OLLAMA_HOST=127.0.0.1:11434 and restart Ollama.
  echo.
  choice /c YN /m "Continue anyway"
  if errorlevel 2 ( echo Stopped. & pause & exit /b 1 )
) else (
  echo   loopback only. Good.
)

echo.
echo === Judge bench: six cases, both paths ===
echo First verdict loads the model and is slow; after that it stays resident.
echo after that the model stays resident for 30 minutes.
echo.
python judge_bench.py
echo.
echo Read the result above before continuing.
echo   6/6 WORKING           -^> good, carry on.
echo   miss on plain transfer-^> STOP. It will reject every real send.
echo   4/6 or worse          -^> STOP. Too weak to stand behind.
echo.
choice /c YN /m "Did it pass - continue with the launch"
if errorlevel 2 ( echo Stopped. & pause & exit /b 1 )

if not exist "genesis.json"       ( echo genesis.json missing - run run_setup.bat first. & pause & exit /b 1 )
if not exist "covenant_A.db.key"  ( echo covenant_A.db.key missing - run run_setup.bat first. & pause & exit /b 1 )

REM --- BACK UP THE FOUNDER KEY FIRST ----------------------------------------
REM covenant_A.db.key is the founder identity AND the genesis mint key.
REM run_all_tests.sh deletes *.db.key in this folder. Back it up.
if not exist "%USERPROFILE%\.covenant-keys" mkdir "%USERPROFILE%\.covenant-keys" >nul 2>nul
if not exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" (
  copy /y covenant_A.db.key "%USERPROFILE%\.covenant-keys\covenant_A.db.key" >nul
  echo Founder key backed up to %USERPROFILE%\.covenant-keys\
)

REM --- fresh PRODUCTION databases -------------------------------------------
REM Explicit filenames on purpose: a wildcard like nodeA_prod.db* would also
REM delete nodeA_prod.db.key, which is your founder identity.
REM Both nodes ADOPT genesis.json rather than minting -- see
REM SANDBOX_VERIFICATION_2026-08-22.md section 3: a node run against the
REM MINTING db reads the founder balance as 0 for a year and forks silently.
if exist "nodeA_prod.db"     del /q "nodeA_prod.db"
if exist "nodeA_prod.db-wal" del /q "nodeA_prod.db-wal"
if exist "nodeA_prod.db-shm" del /q "nodeA_prod.db-shm"
if exist "nodeB_prod.db"     del /q "nodeB_prod.db"
if exist "nodeB_prod.db-wal" del /q "nodeB_prod.db-wal"
if exist "nodeB_prod.db-shm" del /q "nodeB_prod.db-shm"
copy /y covenant_A.db.key nodeA_prod.db.key >nul

set COMMON=set COVENANT_LOCAL_JUDGE_URL=%COVENANT_LOCAL_JUDGE_URL%^&^& set COVENANT_LOCAL_JUDGE_MODEL=%COVENANT_LOCAL_JUDGE_MODEL%^&^& set COVENANT_LOCAL_JUDGE_TIMEOUT=300^&^& set COVENANT_JUDGE_TIMEOUT=300^&^& set COVENANT_OLLAMA_NUM_PREDICT=160^&^& set COVENANT_OLLAMA_NUM_CTX=2048^&^& set COVENANT_OLLAMA_KEEP_ALIVE=30m

echo.
echo Starting node A (port 5000, LIVE, tuned local judge)...
start "Covenant Node A (LIVE ollama)" cmd /k "set COVENANT_DB_PATH=nodeA_prod.db&& %COMMON%&& python run_with_ollama_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021"
echo Starting node B (port 5020, LIVE, tuned local judge)...
start "Covenant Node B (LIVE ollama)" cmd /k "set COVENANT_DB_PATH=nodeB_prod.db&& %COMMON%&& python run_with_ollama_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001"

echo Waiting ~20s for nodes to come up and peer...
timeout /t 20 /nobreak >nul

echo == LIVE run through the TUNED local ethics gate == > live_out.txt
echo -- judge in use -->> live_out.txt
curl -s -m 8 http://127.0.0.1:5000/health >> live_out.txt 2>&1
echo. >> live_out.txt
echo -- founder balance (expect 1000) -->> live_out.txt
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> live_out.txt 2>&1
echo -- send 10 A-^>B (the local model judges this) -->> live_out.txt
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
echo Tip-hash equality is NOT state equality -- compare the balances,
echo not just "converged: True". See SANDBOX_VERIFICATION section 3.
echo.
echo Saved to live_out.txt. Tell Claude "done" and it will read it.
pause
endlocal

@echo off
REM ============================================================================
REM  covenant_go.bat -- the whole sequence, unattended, no prompts.
REM
REM   1. start Ollama with the tuned server settings applied to ITS process
REM   2. pull qwen3:8b if missing
REM   3. run judge_bench.py (fit check + six cases)
REM   4. launch the two nodes ONLY if the bench says 6/6
REM   5. run one real transfer through the gate
REM
REM  Everything lands in go_out.txt. Nothing prompts, so it can run while
REM  nobody is watching. Step 4 is gated on the bench PROGRAMMATICALLY --
REM  no human eyeballing a number and clicking Y.
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set LOG=go_out.txt
echo === covenant_go.bat  %DATE% %TIME% === > %LOG%

REM -- tuned OLLAMA SERVER settings. These are set BEFORE ollama serve is
REM -- started below, so the server process inherits them. No setx, no
REM -- restart dance, nothing persisted to your user environment.
set OLLAMA_HOST=127.0.0.1:11434
set OLLAMA_NUM_PARALLEL=1
set OLLAMA_MAX_LOADED_MODELS=1
set OLLAMA_KEEP_ALIVE=30m
set OLLAMA_FLASH_ATTENTION=1
set OLLAMA_KV_CACHE_TYPE=q8_0
set OLLAMA_CONTEXT_LENGTH=2048

REM -- judge wiring
set COVENANT_LOCAL_JUDGE_URL=http://127.0.0.1:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b
set COVENANT_LOCAL_JUDGE_TIMEOUT=600
set COVENANT_JUDGE_TIMEOUT=600
set COVENANT_JUDGE_PROVIDERS=local
set "COVENANT_INSECURE_MOCK_JUDGE="
set COVENANT_OLLAMA_NUM_PREDICT=160
set COVENANT_OLLAMA_NUM_CTX=2048
set COVENANT_OLLAMA_KEEP_ALIVE=30m

echo. & echo [1/5] Ollama
echo ---- [1/5] Ollama ---- >> %LOG%
curl -s -m 5 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  echo   not running - starting it with the tuned settings...
  echo   server was down; started by this script >> %LOG%
  start "Ollama (tuned)" /min cmd /c "ollama serve"
  timeout /t 12 /nobreak >nul
) else (
  echo   already running ^(tuned settings NOT applied - it was started elsewhere^)
  echo   server already running; tuned env NOT applied to it >> %LOG%
)
curl -s -m 8 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  echo   FAILED - Ollama is not answering. Stopping.
  echo   FAILED: no response on 11434 >> %LOG%
  goto :done
)
echo   up.
ollama --version >> %LOG% 2>&1

echo. & echo [2/5] Model
echo. >> %LOG% & echo ---- [2/5] model ---- >> %LOG%
ollama list | findstr /c:"qwen3:8b" >nul 2>nul
if %errorlevel% neq 0 (
  echo   qwen3:8b not present - pulling ~5.2GB, this takes a few minutes...
  echo   pulling qwen3:8b >> %LOG%
  ollama pull qwen3:8b
) else (
  echo   qwen3:8b already present.
)
ollama list >> %LOG% 2>&1

echo. & echo [3/5] Judge bench - fit check plus six cases
echo. >> %LOG% & echo ---- [3/5] judge_bench ---- >> %LOG%
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
python judge_bench.py --quick
type judge_bench_out.txt >> %LOG% 2>&1

findstr /c:"WORKING on all six" judge_bench_out.txt >nul 2>nul
if %errorlevel% neq 0 (
  echo.
  echo   Bench did NOT pass 6/6. NOT launching.
  echo   BENCH FAILED - launch skipped >> %LOG%
  goto :done
)
echo   6/6. Proceeding.
echo   BENCH PASSED 6/6 >> %LOG%

echo. & echo [4/5] Launching nodes
echo. >> %LOG% & echo ---- [4/5] launch ---- >> %LOG%
if not exist "genesis.json"      ( echo   genesis.json missing. & echo   genesis.json missing >> %LOG% & goto :done )
if not exist "covenant_A.db.key" ( echo   covenant_A.db.key missing. & echo   key missing >> %LOG% & goto :done )

if not exist "%USERPROFILE%\.covenant-keys" mkdir "%USERPROFILE%\.covenant-keys" >nul 2>nul
if not exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" (
  copy /y covenant_A.db.key "%USERPROFILE%\.covenant-keys\covenant_A.db.key" >nul
  echo   founder key backed up to %USERPROFILE%\.covenant-keys\ >> %LOG%
)

REM Explicit filenames: a wildcard would also delete nodeA_prod.db.key,
REM which is the founder identity. Both nodes ADOPT genesis.json rather than
REM minting -- a node on the MINTING db reads founder balance 0 for a year
REM and forks silently (SANDBOX_VERIFICATION section 3).
if exist "nodeA_prod.db"     del /q "nodeA_prod.db"
if exist "nodeA_prod.db-wal" del /q "nodeA_prod.db-wal"
if exist "nodeA_prod.db-shm" del /q "nodeA_prod.db-shm"
if exist "nodeB_prod.db"     del /q "nodeB_prod.db"
if exist "nodeB_prod.db-wal" del /q "nodeB_prod.db-wal"
if exist "nodeB_prod.db-shm" del /q "nodeB_prod.db-shm"
copy /y covenant_A.db.key nodeA_prod.db.key >nul

set CE=set COVENANT_LOCAL_JUDGE_URL=%COVENANT_LOCAL_JUDGE_URL%^&^& set COVENANT_LOCAL_JUDGE_MODEL=%COVENANT_LOCAL_JUDGE_MODEL%^&^& set COVENANT_LOCAL_JUDGE_TIMEOUT=600^&^& set COVENANT_JUDGE_TIMEOUT=600^&^& set COVENANT_OLLAMA_NUM_PREDICT=160^&^& set COVENANT_OLLAMA_NUM_CTX=2048^&^& set COVENANT_OLLAMA_KEEP_ALIVE=30m
start "Covenant Node A" cmd /k "set COVENANT_DB_PATH=nodeA_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021"
start "Covenant Node B" cmd /k "set COVENANT_DB_PATH=nodeB_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001"
echo   both nodes started. waiting 25s to peer...
timeout /t 25 /nobreak >nul

echo. & echo [5/5] One real transfer through the gate
echo. >> %LOG% & echo ---- [5/5] live transfer ---- >> %LOG%
echo -- health -->> %LOG%
curl -s -m 10 http://127.0.0.1:5000/health >> %LOG% 2>&1
echo. >> %LOG%
echo -- founder balance, expect 1000 -->> %LOG%
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> %LOG% 2>&1
echo -- send 10 A to B, the model judges this -->> %LOG%
python covenant_client.py --port 5000 --key nodeA_prod.db.key send --to-key nodeB_prod.db.key --amount 10 >> %LOG% 2>&1
echo -- mine -->> %LOG%
python covenant_client.py --port 5000 --key nodeA_prod.db.key mine >> %LOG% 2>&1
timeout /t 10 /nobreak >nul
echo -- status -->> %LOG%
python covenant_client.py status --ports 5000,5020 >> %LOG% 2>&1
echo -- balances on BOTH dbs, they MUST agree -->> %LOG%
python covenant_client.py balance --db nodeA_prod.db --of-key nodeA_prod.db.key >> %LOG% 2>&1
python covenant_client.py balance --db nodeB_prod.db --of-key nodeA_prod.db.key >> %LOG% 2>&1
python covenant_client.py balance --db nodeA_prod.db --of-key nodeB_prod.db.key >> %LOG% 2>&1
python covenant_client.py balance --db nodeB_prod.db --of-key nodeB_prod.db.key >> %LOG% 2>&1

:done
echo. >> %LOG%
echo === finished %DATE% %TIME% === >> %LOG%
echo.
echo ============================================================
type %LOG%
echo ============================================================
echo Everything above is saved in go_out.txt.
pause
endlocal

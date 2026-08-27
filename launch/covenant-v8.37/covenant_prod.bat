@echo off
REM ============================================================================
REM  covenant_prod.bat -- production start/stop/status. NOT a test rig.
REM
REM  The difference from covenant_go.bat, which is a test rig:
REM
REM    covenant_go.bat   DELETES nodeA_prod.db / nodeB_prod.db on every run.
REM                      Correct for a repeatable test. Catastrophic in
REM                      production -- it discards the chain.
REM    covenant_prod.bat NEVER deletes a database. It creates one only if
REM                      none exists, and otherwise resumes.
REM
REM  It also does not prompt, does not wipe, does not ask you to read a number
REM  and click Y, and starts a watchdog that restarts a dead node and checks
REM  for the fork that tip-hash equality cannot see.
REM
REM  USAGE
REM    covenant_prod.bat            start (idempotent - safe to re-run)
REM    covenant_prod.bat stop
REM    covenant_prod.bat status
REM ============================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"
if not exist "logs" mkdir logs >nul 2>nul
set LOG=logs\prod.log

if /i "%~1"=="stop"   goto :stop
if /i "%~1"=="status" goto :status

REM -- judge wiring (production values) ---------------------------------------
set COVENANT_LOCAL_JUDGE_URL=http://127.0.0.1:11434/v1/chat/completions
if "%COVENANT_LOCAL_JUDGE_MODEL%"=="" set COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b
set COVENANT_LOCAL_JUDGE_TIMEOUT=600
set COVENANT_JUDGE_TIMEOUT=600
set COVENANT_JUDGE_PROVIDERS=local
set "COVENANT_INSECURE_MOCK_JUDGE="
set COVENANT_OLLAMA_NUM_PREDICT=96
set COVENANT_OLLAMA_NUM_CTX=2048
REM 60m -> 30m, 2026-08-22. Measured on this box: the model is 5.2 GB and
REM free RAM was 2.8 GB WITH it loaded, so Windows was already compressing to
REM cope. The chain sat at height 3 through 431 watchdog ticks -- a 60-minute
REM hold was keeping 5.2 GB resident for an hour after a transaction that may
REM not come for a day. 30m is not a new number: it is what OLLAMA_TUNING.md
REM measured and what covenant_go.bat already used. This line was the only
REM place that disagreed. The timer resets on every verdict, so a burst still
REM runs warm; the cost is one cold load -- measured today at 39.9s against
REM 12.1s warm -- on the first transaction after a quiet half hour.
set COVENANT_OLLAMA_KEEP_ALIVE=30m

call :stamp "start requested, model %COVENANT_LOCAL_JUDGE_MODEL%"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

REM -- preflight: Ollama ------------------------------------------------------
curl -s -m 8 http://127.0.0.1:11434/api/tags >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "ABORT: Ollama not answering on 11434. A judge that cannot be reached fails CLOSED - every transaction rejected."
  echo Ollama is not running. Start it, then re-run.
  exit /b 1
)

REM -- preflight: does the model fit? -----------------------------------------
python -c "import sys,os;sys.path.insert(0,'.');from judge_bench import fit_check,OUT;ok=fit_check();print('\n'.join(OUT));sys.exit(0 if ok else 1)"
if %errorlevel% neq 0 (
  call :stamp "ABORT: model does not fit or is not installed - see above"
  exit /b 1
)

REM -- first run only: create the databases. NEVER delete an existing one. ----
if not exist "genesis.json"      ( call :stamp "ABORT: genesis.json missing" & exit /b 1 )
if not exist "covenant_A.db.key" ( call :stamp "ABORT: covenant_A.db.key missing" & exit /b 1 )
if not exist "%USERPROFILE%\.covenant-keys" mkdir "%USERPROFILE%\.covenant-keys" >nul 2>nul
if not exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" copy /y covenant_A.db.key "%USERPROFILE%\.covenant-keys\covenant_A.db.key" >nul
if not exist "nodeA_prod.db.key" copy /y covenant_A.db.key nodeA_prod.db.key >nul
if exist "nodeA_prod.db" ( call :stamp "resuming existing nodeA_prod.db" ) else ( call :stamp "first run - nodeA_prod.db will be created by adopting genesis.json" )
if exist "nodeB_prod.db" ( call :stamp "resuming existing nodeB_prod.db" ) else ( call :stamp "first run - nodeB_prod.db will be created by adopting genesis.json" )

REM -- start each node only if its port is not already listening --------------
set CE=set COVENANT_LOCAL_JUDGE_URL=%COVENANT_LOCAL_JUDGE_URL%^&^& set COVENANT_LOCAL_JUDGE_MODEL=%COVENANT_LOCAL_JUDGE_MODEL%^&^& set COVENANT_LOCAL_JUDGE_TIMEOUT=600^&^& set COVENANT_JUDGE_TIMEOUT=600^&^& set COVENANT_OLLAMA_NUM_PREDICT=96^&^& set COVENANT_OLLAMA_NUM_CTX=2048^&^& set COVENANT_OLLAMA_KEEP_ALIVE=30m

curl -s -m 5 http://127.0.0.1:5000/health >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "starting node A on 5000"
  start "Covenant Node A" /min cmd /c "set COVENANT_DB_PATH=nodeA_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021 >> logs\nodeA.log 2>&1"
) else ( call :stamp "node A already up" )

curl -s -m 5 http://127.0.0.1:5020/health >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "starting node B on 5020"
  start "Covenant Node B" /min cmd /c "set COVENANT_DB_PATH=nodeB_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001 >> logs\nodeB.log 2>&1"
) else ( call :stamp "node B already up" )

timeout /t 20 /nobreak >nul

REM -- watchdog: one only -----------------------------------------------------
tasklist /v /fi "imagename eq python.exe" 2>nul | findstr /i "watchdog" >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "starting watchdog"
  start "Covenant Watchdog" /min cmd /c "%CE%&& python covenant_watchdog.py --interval 60 >> logs\watchdog-stdout.log 2>&1"
) else ( call :stamp "watchdog already running" )

timeout /t 5 /nobreak >nul
call :stamp "start complete"
goto :status

:status
echo.
echo === Covenant status ===
for %%P in (5000 5020) do (
  curl -s -m 6 http://127.0.0.1:%%P/health > "%TEMP%\cov_h.json" 2>nul
  if !errorlevel! equ 0 (
    echo   node on %%P: UP
    python -c "import json;d=json.load(open(r'%TEMP%\cov_h.json'));print('     height',d.get('chain_height'),'peers',d.get('peers'),'judge',d.get('judge'),'insecure',d.get('judge_insecure'))" 2>nul
  ) else ( echo   node on %%P: DOWN )
)
echo.
echo   watchdog verdict:
python covenant_watchdog.py --once
if %errorlevel% neq 0 ( echo   ^>^> ALERTS above. ) else ( echo   ^>^> all checks passed. )
echo.
echo   logs\  prod.log nodeA.log nodeB.log watchdog.log
exit /b 0

:stop
call :stamp "stop requested"
taskkill /fi "windowtitle eq Covenant Node A*" /f >nul 2>nul
taskkill /fi "windowtitle eq Covenant Node B*" /f >nul 2>nul
taskkill /fi "windowtitle eq Covenant Watchdog*" /f >nul 2>nul
call :stamp "stopped. Databases untouched - covenant_prod.bat resumes them."
echo Stopped. Nothing was deleted.
exit /b 0

:stamp
echo %DATE% %TIME%  %~1>> %LOG%
echo %~1
exit /b 0

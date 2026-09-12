@echo off
REM ============================================================================
REM  covenant_prod.bat -- production start/stop/status. NOT a test rig.
REM
REM  covenant_prod.bat NEVER deletes a database. It creates one only if none
REM  exists, and otherwise resumes. (A test rig that did delete them,
REM  covenant_go.bat, was removed on 2026-09-12 with the model server it drove.)
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
REM 2026-09-12: no local model server URL or model tag is set here any more;
REM the server they named was removed from this PC on 2026-09-07.
set COVENANT_LOCAL_JUDGE_TIMEOUT=600
set COVENANT_JUDGE_TIMEOUT=600
REM v8.40 (2026-08-29): the semantic judge rides in the quorum, not on
REM the bench. The smoke boot of this landing printed the core's own
REM hint ('add it to COVENANT_JUDGE_PROVIDERS to use it') -- a judge
REM shipped and wired to nothing is the defect class this repo keeps
REM finding in itself, caught this time BEFORE the restart.
set COVENANT_JUDGE_PROVIDERS=deferring,semantic
REM 2026-09-12: was local,semantic; the launcher's no-policy default changed (A93).
REM 2026-09-03: ops\quorum_policy.json overrides the line above at node start
REM (the launcher applies it; the watchdog reads it too). It says
REM "deferring,semantic": seat 0 is "deferring" -- the two distilled students,
REM in-process -- and "semantic" is the deterministic lexical judge. Delete that
REM file to get exactly the line above, which since 2026-09-12 means the same.
set "COVENANT_INSECURE_MOCK_JUDGE="

call :stamp "start requested"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

REM -- preflight: none for a model server (2026-09-12) ------------------------
REM Until today this file probed port 11434 and ABORTED when nothing answered,
REM which on any tree without the gitignored ops\quorum_policy.json -- every
REM clone -- meant it could not start at all (a LIVE defect). The server was
REM removed on 2026-09-07; the judge is the distilled student, in-process. A
REM start is never blocked by a missing server; the gate itself fails closed.

REM -- first run only: create the databases. NEVER delete an existing one. ----
if not exist "genesis.json"      ( call :stamp "ABORT: genesis.json missing" & exit /b 1 )
if not exist "covenant_A.db.key" ( call :stamp "ABORT: covenant_A.db.key missing" & exit /b 1 )
if not exist "%USERPROFILE%\.covenant-keys" mkdir "%USERPROFILE%\.covenant-keys" >nul 2>nul
if not exist "%USERPROFILE%\.covenant-keys\covenant_A.db.key" copy /y covenant_A.db.key "%USERPROFILE%\.covenant-keys\covenant_A.db.key" >nul
if not exist "nodeA_prod.db.key" copy /y covenant_A.db.key nodeA_prod.db.key >nul
if exist "nodeA_prod.db" ( call :stamp "resuming existing nodeA_prod.db" ) else ( call :stamp "first run - nodeA_prod.db will be created by adopting genesis.json" )
if exist "nodeB_prod.db" ( call :stamp "resuming existing nodeB_prod.db" ) else ( call :stamp "first run - nodeB_prod.db will be created by adopting genesis.json" )
if exist "nodeC_prod.db" ( call :stamp "resuming existing nodeC_prod.db" ) else ( call :stamp "first run - nodeC_prod.db will be created by adopting genesis.json" )

REM -- start each node only if its port is not already listening --------------
set CE=set COVENANT_LOCAL_JUDGE_TIMEOUT=600^&^& set COVENANT_JUDGE_TIMEOUT=600

curl -s -m 5 http://127.0.0.1:5000/health >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "starting node A on 5000"
  start "Covenant Node A" /min cmd /c "set COVENANT_DB_PATH=nodeA_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5000 --node-id A --genesis genesis.json --peers 127.0.0.1:5021 >> logs\nodeA.log 2>&1"
) else ( call :stamp "node A already up" )

curl -s -m 5 http://127.0.0.1:5020/health >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "starting node B on 5020"
  start "Covenant Node B" /min cmd /c "set COVENANT_DB_PATH=nodeB_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5020 --node-id B --genesis genesis.json --peers 127.0.0.1:5001,127.0.0.1:5061 >> logs\nodeB.log 2>&1"
) else ( call :stamp "node B already up" )

REM -- node C. Port arithmetic (M2): --port N takes N, N+1 and N+11, so nodes
REM must sit at least 20 apart. A=5000/5001/5011, B=5020/5021/5031,
REM C=5060/5061/5071. The obvious 5040 was MEASURED taken on this
REM machine -- svchost.exe, WinError 10048 -- so C moved.
REM AO_PORT_PICK.bat bind-probes for a free block rather than
REM guessing, because netstat cannot see Windows' excluded port
REM ranges and a port can be free in netstat and unbindable.
REM --peers takes each peer's P2P port (API+1), not its API
REM port; get that wrong and both nodes report healthy while neither hears the
REM other. preflight_port_check catches both since v8.15.
curl -s -m 5 http://127.0.0.1:5060/health >nul 2>nul
if %errorlevel% neq 0 (
  call :stamp "starting node C on 5060"
  start "Covenant Node C" /min cmd /c "set COVENANT_DB_PATH=nodeC_prod.db&& %CE%&& python run_with_ollama_judge.py --port 5060 --node-id C --genesis genesis.json --peers 127.0.0.1:5021 >> logs\nodeC.log 2>&1"
) else ( call :stamp "node C already up" )

timeout /t 20 /nobreak >nul

REM -- watchdog: one only -----------------------------------------------------
REM  FIXED 2026-09-08. This check used to be
REM      tasklist /v /fi "imagename eq python.exe" | findstr /i "watchdog"
REM  and it never once matched. `tasklist /v` searches the WINDOW TITLE column,
REM  and measured today every python.exe on this machine reports its title as
REM  "N/A" -- including the watchdog that was running at the time. So findstr
REM  found nothing, errorlevel was always 1, and the "one only" guard started
REM  ANOTHER watchdog on every single run. That is how two came to be running
REM  (PID 5248 from 09-07 10:46 on stale source, PID 26012 from 09-08 05:52):
REM  each mined the pool once a minute, so each rate-limited the other into
REM  HTTP 429, and each appended its own contradictory verdict to
REM  ops/SELF_EVAL.md -- which is why that ledger alternated self PASS and
REM  self FAIL every hour and neither was wrong.
REM
REM  Match on the COMMAND LINE, which is the only thing that actually
REM  identifies this process. `.Where({...})` avoids a pipe, which would need
REM  escaping inside a batch line. Exit 0 = a watchdog is already running.
powershell -NoProfile -Command "$a=@(Get-CimInstance Win32_Process -Filter 'Name LIKE ''python%%'''); $w=$a.Where({$_.CommandLine -like '*covenant_watchdog.py*'}); exit [int]($w.Count -eq 0)"
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
for %%P in (5000 5020 5060) do (
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
echo   logs\  prod.log nodeA.log nodeB.log nodeC.log watchdog.log
exit /b 0

:stop
call :stamp "stop requested"
taskkill /fi "windowtitle eq Covenant Node A*" /f >nul 2>nul
taskkill /fi "windowtitle eq Covenant Node B*" /f >nul 2>nul
taskkill /fi "windowtitle eq Covenant Node C*" /f >nul 2>nul
taskkill /fi "windowtitle eq Covenant Watchdog*" /f >nul 2>nul
call :stamp "stopped. Databases untouched - covenant_prod.bat resumes them."
echo Stopped. Nothing was deleted.
exit /b 0

:stamp
echo %DATE% %TIME%  %~1>> %LOG%
echo %~1
exit /b 0

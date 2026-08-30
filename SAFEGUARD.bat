@echo off
REM ===========================================================================
REM  SAFEGUARD.bat -- one double-click for "make sure the record survives me".
REM  2026-08-30.
REM
REM  GO.bat publishes the CODE. This publishes nothing and protects the RECORD:
REM  verify it, copy it three ways, show its fingerprint, and list what is still
REM  open. The two are complementary and neither replaces the other.
REM
REM  WHAT IT DOES ON ITS OWN
REM    1. Verifies the memory store. If it does not verify, it stops. Backing up
REM       a store you cannot vouch for spreads the error instead of catching it.
REM    2. Copies it to a second folder, to OneDrive, and commits it to a LOCAL
REM       git repo. Three copies, one of them off this machine.
REM    3. Re-runs the standalone corrective's own assertions.
REM
REM  WHAT IT REFUSES TO DO, DELIBERATELY
REM    Change firewall or security settings. Restart the live chain. Send a
REM    message to another person. Those are printed with the exact command so
REM    that if they happen, you did them knowingly.
REM
REM  The store is NEVER pushed to GitHub. It names people who did not consent
REM  and carries one person's medical detail. Only its fingerprint is public.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- SAFEGUARD
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
set STORE=%USERPROFILE%\ai_memory
set STAMP=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%

echo.
echo   ==========================================================
echo    STEP 1 of 6 -- verify the record
echo   ==========================================================
if not exist "%STORE%" goto NOSTORE
set AI_MEMORY_ROOT=%STORE%
REM Logic in Python, not inline: cmd eats a bare %, which corrupted the format
REM specifiers and made this report "does not verify" on a healthy record.
"%PY%" safeguard_check.py
set RC=%ERRORLEVEL%
if "%RC%"=="2" goto NOSTORE
if not "%RC%"=="0" goto DRIFTED

echo.
echo   ==========================================================
echo    STEP 2 of 6 -- three copies
echo   ==========================================================
if not exist "%USERPROFILE%\ai_memory_backups\%STAMP%" mkdir "%USERPROFILE%\ai_memory_backups\%STAMP%" >nul 2>&1
copy /Y "%STORE%\*.md" "%USERPROFILE%\ai_memory_backups\%STAMP%\" >nul 2>&1
copy /Y "%STORE%\audit.jsonl" "%USERPROFILE%\ai_memory_backups\%STAMP%\" >nul 2>&1
echo     disk   : ai_memory_backups\%STAMP%
if not exist "%USERPROFILE%\OneDrive" goto NOCLOUD
if not exist "%USERPROFILE%\OneDrive\covenant-memory-backup\%STAMP%" mkdir "%USERPROFILE%\OneDrive\covenant-memory-backup\%STAMP%" >nul 2>&1
copy /Y "%STORE%\*.md" "%USERPROFILE%\OneDrive\covenant-memory-backup\%STAMP%\" >nul 2>&1
copy /Y "%STORE%\audit.jsonl" "%USERPROFILE%\OneDrive\covenant-memory-backup\%STAMP%\" >nul 2>&1
echo     cloud  : OneDrive\covenant-memory-backup\%STAMP%
goto HISTORY
:NOCLOUD
echo     cloud  : SKIPPED, no OneDrive folder
:HISTORY
cd /d "%STORE%"
git add -A >nul 2>&1
git commit -q -m "snapshot %STAMP%" >nul 2>&1
echo     history: local git commit (never pushed)
cd /d "%~dp0"

echo.
echo   ==========================================================
echo    STEP 3 of 6 -- the shareable part still holds
echo   ==========================================================
"%PY%" refutable.py selftest

echo.
echo   ==========================================================
echo    STEP 4 of 6 -- is this machine exposed right now?
echo   ==========================================================
REM The node watches its peers and its traffic; nothing in it watches
REM its own posture. This asks the question it never asks itself.
"%PY%" exposure_check.py

echo.
echo   ==========================================================
echo    STEP 5 of 6 -- is the TOP of the supervision chain running?
echo   ==========================================================
REM The watchdog revives nodes, the guard revives the watchdog, and nothing
REM sits above the guard. test_c2 already reads the WATCHDOG's silence; nothing
REM read the GUARD's -- so the one process with nothing above it was the one
REM whose silence nobody listened for. It reports HISTORY as well as "now",
REM because a guard gated off on battery resumes on mains and reads healthy
REM every time anyone looks while plugged in.
"%PY%" guard_freshness.py

echo.
echo   ==========================================================
echo    STEP 6 of 6 -- what could this do with funds right now?
echo   ==========================================================
REM Both easy readings are wrong and the true one changes with a config flag,
REM so it is measured rather than asserted. Reads no key, places nothing,
REM arms nothing. If it ever prints ARMED, CONSTITUTION.md II.1 is being
REM broken and the documents are out of date.
"%PY%" money_posture.py

echo.
echo   ==========================================================
echo    STILL OPEN -- these need you, not me
echo   ==========================================================
echo.
echo    A. EXPORT THE CORPUS. ~110 conversations exist only in vendor
echo       interfaces. This is the part that dies with account access.
echo         ChatGPT  Settings, Data controls, Export
echo         Claude   Settings, Account, Export data
echo         Gemini   takeout.google.com
echo         Mistral  Settings, Data
echo         DeepSeek Profile, Data export
echo       Then: "%PY%" ai_memory_system\import_conversations.py FILE
echo.
echo    B. SEND THE MESSAGES. docs\OUTREACH.md has five drafts.
echo       Schoff first, he already knows you. Chella second, it matters most.
echo.
goto DONE

:NOSTORE
echo     No store at %STORE% -- nothing to safeguard.
goto DONE

:DRIFTED
echo.
echo     STOPPED. The record does not verify.
echo     Backing up a store you cannot vouch for spreads the error.
echo     Fix the drift first; the audit chain says where.
goto DONE

:DONE
echo   ==========================================================
echo    Public:  github.com/LAWLESS1987/covenant
echo             docs\WHAT_WE_FOUND.md   the findings
echo             refutable.py            the corrective, take it
echo    Private: %STORE%   (never pushed, only its root is)
echo   ==========================================================
echo.
pause
endlocal

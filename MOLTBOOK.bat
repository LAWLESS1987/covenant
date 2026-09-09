@echo off
REM ===========================================================================
REM  MOLTBOOK.bat -- let Ora learn from the forum. 2026-09-08.
REM
REM    MOLTBOOK.bat            selftest, then a DRY RUN. Writes nothing.
REM    MOLTBOOK.bat RELEASE    judge up to 5 quarantined rows and write them
REM                            to ops/verdicts.jsonl.
REM
REM  WHY THE ARGUMENT. Releasing writes to the corpus the ethics judge distils
REM  from, and that judge gates the trading program. A double-click should not
REM  be able to do that by accident, so the default is the harmless half. Same
REM  reasoning as AB_RESTART_NODES.bat needing FORCE.
REM
REM  WHO LABELS. Not the post, not the students, not the assistant that
REM  harvested them -- the GitHub runner, the only judge here that answers on
REM  unfamiliar text. A row it does not answer on is NOT released.
REM
REM  WHO LEARNS. Released rows carry source "moltbook/judged", which
REM  covenant_second_student pins to half 0. Ora trains on the whole ledger and
REM  sees them. SENA NEVER DOES -- she is the control, and the comparison
REM  between them is the entire point of the arrangement.
REM
REM  NOT YET VERIFIED. As of 2026-09-08 the selftest below had never been run:
REM  the session that wrote it could not execute commands. Run this with no
REM  argument first and read what it says before you ever pass RELEASE.
REM
REM  NO LABELS AND NO GOTO ON PURPOSE. This file was written by a tool that
REM  emits LF line endings, and cmd.exe can fail to find a label in an LF file
REM  -- a launcher that silently skips its own steps is worse than none. Two
REM  sequential IFs do the same job and cannot.
REM
REM  M28: no bare "(" outside a REM.
REM ===========================================================================
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo.
echo  ==== 1 of 2: selftest -- offline, stub teacher, writes nothing ====
echo.
python covenant_moltbook_release.py --selftest
echo.
echo  selftest exit code %errorlevel%   -- must be 0 before anything else
echo.

if /I not "%~1"=="RELEASE" echo  ==== 2 of 2: dry run -- shows what would go, writes nothing ====
if /I not "%~1"=="RELEASE" python covenant_moltbook_release.py

if /I "%~1"=="RELEASE" echo  ==== 2 of 2: RELEASE -- judging rows and WRITING the corpus ====
if /I "%~1"=="RELEASE" python covenant_moltbook_release.py --release --limit 5

echo.
echo  Done. To actually release:  MOLTBOOK.bat RELEASE
echo  Afterwards, re-run the exam and compare Ora against Sena -- if the
echo  control moved too, something routed a moltbook row into half 1.
echo.
pause

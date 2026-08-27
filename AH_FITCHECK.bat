@echo off
REM AH_FITCHECK.bat -- prints the fit check only. Loads nothing, changes
REM nothing, takes about a second. 2026-08-22.
setlocal
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
set COVENANT_LOCAL_JUDGE_URL=http://127.0.0.1:11434/v1/chat/completions
set COVENANT_LOCAL_JUDGE_MODEL=qwen3:8b
> FIT_CHECK.txt echo ==== fit check %DATE% %TIME% ====
"%PY%" -c "import sys;sys.path.insert(0,'.');from judge_bench import fit_check,OUT;ok=fit_check();print('\n'.join(OUT));print('returned',ok)" >> FIT_CHECK.txt 2>&1
type FIT_CHECK.txt
echo.
pause
endlocal

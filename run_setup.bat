@echo off
REM ============================================================
REM  Covenant one-click setup + readiness check (Windows)
REM  Run in a terminal:  run_setup.bat
REM  Sets up Python, mints your genesis, writes preflight_out.txt
REM ============================================================
setlocal
cd /d "%~dp0"

REM db path for the node is controlled by this env var (there is no --db flag)
set COVENANT_DB_PATH=covenant_A.db

echo.
echo === Covenant setup ===
echo Folder: %cd%
echo.

where python >nul 2>nul
if %errorlevel%==0 (set PY=python) else (set PY=py)
echo Using Python launcher: %PY%
%PY% --version
if %errorlevel% neq 0 (
  echo.
  echo ERROR: Python not found. Install Python 3.10+ from python.org
  echo        with "Add python.exe to PATH", then run this again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo Creating virtual environment .venv ...
  %PY% -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo Installing dependencies ...
python -m pip install --upgrade pip >nul 2>nul
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
  echo WARNING: dependency install reported a problem; the check below shows what is missing.
)

echo.
set "ANTHROPIC_API_KEY="
set /p ANTHROPIC_API_KEY=Paste your Anthropic API key (or press Enter to skip for now):
set COVENANT_JUDGE_PROVIDERS=claude
set "COVENANT_INSECURE_MOCK_JUDGE="

REM -- mint the shared genesis once (db path comes from COVENANT_DB_PATH above) --
if not exist "genesis.json" (
  echo Minting shared genesis ...
  python covenant_unified_v8.py --export-genesis genesis.json
) else (
  echo genesis.json already exists - keeping it.
)

echo.
echo Running readiness check -^> preflight_out.txt
python preflight.py --genesis genesis.json --db covenant_A.db > preflight_out.txt 2>&1

echo.
echo ============================================================
type preflight_out.txt
echo ============================================================
echo.
echo Done. Report saved as preflight_out.txt. Tell Claude "done".
echo.
pause
endlocal

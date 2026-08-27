@echo off
REM ============================================================================
REM  covenant_anchor.bat -- put the seal root into the chain.
REM
REM  Re-seals first (so the root reflects the folder as it is right now),
REM  then submits one transaction carrying that root, mines it, and reads the
REM  chain back to confirm.
REM
REM  The anchor goes through the ethics gate like anything else. If the gate
REM  rejects it, nothing is written and that is the gate working.
REM ============================================================================
setlocal
cd /d "%~dp0"
set KEY=%USERPROFILE%\.covenant-keys\covenant_A.db.key
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo.
echo === 1/3  Re-seal so the root is current ===
python covenant_seal.py manifest
python covenant_seal.py public
python covenant_seal.py encrypt --keyfile "%KEY%"

echo.
echo === 2/3  Anchor it in the chain ===
python covenant_anchor.py --port 5000

echo.
echo === 3/3  Verify ===
python covenant_anchor.py --check --port 5000

echo.
echo ============================================================
echo  SEAL_ANCHOR.json holds the block index and hash.
echo.
echo  Read this part: the chain you anchored to is one you run
echo  end to end. That makes tampering DETECTABLE, not IMPOSSIBLE.
echo  For proof anyone else would accept, the root has to reach
echo  someone who is not you. SEAL_PUBLIC.txt is safe to send whole.
echo ============================================================
pause
endlocal

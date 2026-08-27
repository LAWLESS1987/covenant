@echo off
REM ============================================================================
REM  covenant_unlock_test.bat -- prove the archive opens.
REM
REM  An encrypted file that has never been opened is a guess, not a backup.
REM  This decrypts covenant_sealed.bin into _unsealtest\ using the key file,
REM  then re-hashes what came out and compares it to the sealed root.
REM
REM  Read-only with respect to your real files. It creates _unsealtest\ and
REM  nothing else. Delete that folder yourself when you have seen it work.
REM ============================================================================
setlocal
cd /d "%~dp0"
set KEY=%USERPROFILE%\.covenant-keys\covenant_A.db.key
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

echo.
echo === Decrypting with the key file (no passphrase) ===
python covenant_seal.py decrypt _unsealtest --keyfile "%KEY%"
if %errorlevel% neq 0 (
  echo.
  echo  IT DID NOT OPEN. Do not delete anything. Tell Claude.
  pause & exit /b 1
)

echo.
echo === Independent check: re-hash what came out ===
python -c "import hashlib,os,sys;sys.path.insert(0,'.');import covenant_seal as s;s.HERE=os.path.abspath('_unsealtest');rows=s.build_manifest();print('  files',len(rows));print('  root ',s.root_hash(rows))"
echo.
echo === Sealed root, for comparison ===
python -c "import json;print('  root ',json.load(open('covenant_sealed.json'))['root']);print('  files',json.load(open('covenant_sealed.json'))['files'])"
echo.
echo ============================================================
echo  If those two roots match, the archive is real and it opens.
echo  _unsealtest\ is a copy - delete it when you are satisfied.
echo ============================================================
pause
endlocal

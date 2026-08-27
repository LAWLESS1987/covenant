@echo off
REM ============================================================================
REM  covenant_lock.bat -- seal the folder. Unattended: nothing to type.
REM
REM  Unlock is by POSSESSION of covenant_A.db.key, not by a passphrase. The
REM  copy used is the one in %USERPROFILE%\.covenant-keys\ -- deliberately
REM  OUTSIDE this folder, so the lock and the key are not in the same place.
REM
REM  Three artefacts:
REM    MANIFEST.sha256      every file, size and SHA-256. Proves integrity.
REM    SEAL_PUBLIC.txt      root hash + hashed filenames. Safe to hand to
REM                         anyone: they can verify a file they already hold
REM                         and learn nothing else.
REM    covenant_sealed.bin  AES-256-GCM over the whole folder.
REM
REM  It does NOT delete anything. Your files stay exactly where they are.
REM ============================================================================
setlocal
cd /d "%~dp0"
set KEY=%USERPROFILE%\.covenant-keys\covenant_A.db.key
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

if not exist "%KEY%" (
  echo Key file not found: %KEY%
  echo Run covenant_prod.bat once - it makes that copy - then re-run this.
  pause & exit /b 1
)

echo.
echo === 1/3  Manifest ===
python covenant_seal.py manifest
echo.
echo === 2/3  Public proof ===
python covenant_seal.py public
echo.
echo === 3/3  Sealing (unlock = possession of the key file) ===
python covenant_seal.py encrypt --keyfile "%KEY%"

echo.
echo ============================================================
echo  Nothing was deleted. To prove the archive opens:
echo     python covenant_seal.py decrypt scratch --keyfile "%KEY%"
echo.
echo  This is INTEGRITY now. It becomes SECRECY when
echo  %USERPROFILE%\.covenant-keys\ moves to a USB stick --
echo  no re-sealing needed, just point --keyfile at the new path.
echo ============================================================
pause
endlocal

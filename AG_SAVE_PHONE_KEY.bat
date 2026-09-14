@echo off
REM ===========================================================================
REM  AG_SAVE_PHONE_KEY.bat -- save the phone node's identity key off the phone.
REM
REM  WHY NOW. That key (files/core/covenant_unified_phone.db.key inside the app)
REM  is REGISTERED on this PC as a daily-plan signer: whoever holds it can
REM  approve the day's trading plan, and sealed mail is addressed to it. There
REM  is one copy, on the phone, and an uninstall deletes it.
REM
REM  Two doors are closing at once:
REM    * Switching to the operator's own APK signing key -- the top item of the
REM      2026-09-14 security audit -- forces an uninstall, because a new signing
REM      key is a new app identity. That deletes this key.
REM    * The build from 2026-09-14 is no longer `debuggable`, which is what shut
REM      the hole where anyone with brief USB access could read the app's private
REM      directory. It shuts this route too. The app on the phone TODAY is still
REM      debuggable; the next one will not be.
REM
REM  So run this while the old app is still installed. Afterwards it needs root.
REM
REM  WHAT IT DOES. Finds the adb that ships in this repository, checks exactly
REM  one authorised phone is plugged in, reads the key with `run-as`, checks it
REM  really is a private key, and writes ONE file to
REM  %USERPROFILE%\.covenant\phone-identity\ -- outside every repository, beside
REM  the phone signing key. It refuses to overwrite an existing one. It never
REM  prints the key; it prints the fingerprint of the public half and says
REM  whether that matches the signer this PC has registered as "phone".
REM
REM  Before you start: plug the phone in by USB, unlock it, and make sure
REM  Developer options > USB debugging is on. The phone will ask you to allow
REM  this computer -- say yes.
REM ===========================================================================
setlocal
cd /d "%~dp0"

echo.
echo   Saving the phone node's identity key.
echo.

python mobile\phone_identity_export.py --status
echo.
python mobile\phone_identity_export.py
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo   Done. The key is saved outside every repository.
  echo   You can install the hardened build now.
) else (
  echo   Nothing was saved -- the reason is printed above.
  echo   Nothing on the phone was changed either.
)
echo.
pause
endlocal

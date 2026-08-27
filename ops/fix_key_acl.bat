@echo off
REM ===========================================================================
REM  ops\fix_key_acl.bat -- P9. Set the NTFS ACL that chmod(0600) cannot.
REM
REM  WHAT P9 IS.  covenant_unified_v8.py writes the node identity key with
REM  os.open(..., 0o600) and the audit asserts "identity key file is owner-only".
REM  On NTFS that mode bit is close to meaningless: access is governed by ACLs,
REM  os.stat().st_mode reports 0o666 whatever the ACL says, and Python's chmod
REM  only toggles the read-only attribute. So on this platform the assertion is
REM  not weak -- it is a constant, and it has been failing for that reason.
REM
REM  This applies the control the mode bit was standing in for. It TIGHTENS:
REM  it removes inherited access and grants Full only to you, SYSTEM and
REM  Administrators. It cannot loosen anything, and it touches no code.
REM
REM  It does NOT make MainnetPolicy.load pass -- that check reads the POSIX
REM  mode and will still refuse on Windows. That needs a code change, it is a
REM  change to a security control, and Section 0 says such a change is L's to
REM  approve. The reference implementation and the exact diff are in
REM  ops\owner_only.py and docs\P9_WINDOWS_OWNER_ONLY.md. Nothing here applies
REM  it for you.
REM
REM  Run from the covenant folder:  ops\fix_key_acl.bat
REM ===========================================================================
setlocal
cd /d "%~dp0.."
set OUT=ops\ACL_RESULT.txt

> "%OUT%" echo ==== key ACL tighten  %DATE% %TIME% ====
>> "%OUT%" echo user: %USERNAME%
>> "%OUT%" echo.

if exist "*.db.key" goto HAVEKEYS
echo   No *.db.key in this folder. Nothing to protect yet -- they are
echo   created on the first node start. Run this again afterwards.
>> "%OUT%" echo no *.db.key present
goto SHOW

:HAVEKEYS
for %%K in (*.db.key) do call :one "%%K"
if exist "xrp_mainnet_policy.json" call :one "xrp_mainnet_policy.json"
goto SHOW

:one
echo   tightening %~1
>> "%OUT%" echo --- %~1 ---
icacls "%~1" /inheritance:r >> "%OUT%" 2>&1
icacls "%~1" /grant:r "%USERNAME%":F >> "%OUT%" 2>&1
icacls "%~1" /grant:r "NT AUTHORITY\SYSTEM":F >> "%OUT%" 2>&1
icacls "%~1" /grant:r "BUILTIN\Administrators":F >> "%OUT%" 2>&1
>> "%OUT%" echo --- resulting ACL ---
icacls "%~1" >> "%OUT%" 2>&1
>> "%OUT%" echo.
exit /b 0

:SHOW
echo.
type "%OUT%"
echo.
echo   Verify independently:  python launch_check.py --gate G8
echo.
pause
endlocal

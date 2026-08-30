@echo off
REM ===========================================================================
REM  CLOSE_EXPOSURE.bat -- one click, with the click as the approval.
REM  2026-08-30.
REM
REM  WHAT IT DOES
REM    Adds ONE Windows Firewall rule blocking inbound TCP to the covenant node
REM    ports, then re-runs exposure_check.py to prove it worked rather than
REM    claiming it did.
REM
REM  WHY IT ASKS FIRST
REM    This changes a security setting on your machine. It shows the exact rule
REM    it will add, waits for you to type YES, and Windows shows its own admin
REM    prompt on top of that. Two deliberate acts, both yours.
REM
REM  WHAT IT DOES NOT TOUCH
REM    It does not stop, start or restart any node. It does not edit source. It
REM    does not remove or weaken any existing rule -- a block rule takes
REM    precedence over the broad Python allow rules without deleting them, so
REM    other Python you run is unaffected.
REM
REM  REVERSIBLE
REM    Printed at the end, and here:
REM      netsh advfirewall firewall delete rule name="Covenant nodes - block inbound"
REM
REM  AFTER THIS
REM    The ledger stays readable the way you meant: run public_ledger.py, which
REM    serves /chain read-only and refuses everything else.
REM
REM  M28/rule 9: GOTO labels, no parenthesised IF blocks.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- CLOSE EXPOSURE
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
set RULE=Covenant nodes - block inbound
REM The four base ports this deployment runs, plus the +10 companion each node
REM also binds. Scoped to covenant's own ports rather than a guessed range:
REM a block rule is precise or it is someone else's outage.
REM NOTE: 5000 is a common dev port (Flask and others default to it). If you
REM later want some OTHER program reachable on 5000 from your LAN, this rule
REM will stop it, and the fix is to narrow this rule, not to delete it.
set PORTS=5000,5010,5020,5030,5040,5050,5060,5070

net session >nul 2>&1
if errorlevel 1 goto ELEVATE

echo.
echo   ==========================================================
echo    BEFORE
echo   ==========================================================
"%PY%" exposure_check.py

echo.
echo   ==========================================================
echo    WHAT THIS WILL DO
echo   ==========================================================
echo.
echo     netsh advfirewall firewall add rule ^
echo       name="%RULE%" ^
echo       dir=in action=block protocol=TCP localport=%PORTS%
echo.
echo    One rule. Blocks inbound connections to the node ports from
echo    other machines. Adds nothing else, deletes nothing, and does
echo    not touch the running nodes.
echo.
echo    It does NOT block loopback, so the nodes keep talking to each
echo    other and public_ledger.py keeps reading the chain.
echo.
echo    Reverse it any time with:
echo      netsh advfirewall firewall delete rule name="%RULE%"
echo.
set /p OK=   Type YES to apply, anything else to cancel:
if /i not "%OK%"=="YES" goto CANCELLED

echo.
echo   Applying...
netsh advfirewall firewall delete rule name="%RULE%" >nul 2>&1
netsh advfirewall firewall add rule name="%RULE%" dir=in action=block protocol=TCP localport=%PORTS%
if errorlevel 1 goto FAILED

echo.
echo   ==========================================================
echo    AFTER -- verifying, not assuming
echo   ==========================================================
"%PY%" exposure_check.py
echo.
echo   Note: exposure_check reports what the ALLOW rules permit. The
echo   block rule now takes precedence over them at the firewall, so
echo   the honest confirmation is a connection attempt from another
echo   device on your network. Until you do that, treat this as
echo   "rule applied", not "proven closed".
echo.
echo   ==========================================================
echo    STILL OPEN
echo   ==========================================================
echo.
echo    The nodes still BIND 0.0.0.0. The firewall now stops that
echo    reaching anyone, but the durable fix is the bind itself.
echo    Change the default from 0.0.0.0 to 127.0.0.1 in
echo    covenant_unified_v8.py; it takes effect at the next restart
echo    and costs nothing while every node is on this machine.
echo.
echo    To serve the ledger deliberately:  "%PY%" public_ledger.py --public
echo.
goto DONE

:ELEVATE
echo.
echo   This needs administrator rights to change a firewall rule.
echo   Windows will ask. That prompt is the approval.
echo.
powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
goto EOF

:CANCELLED
echo.
echo   Cancelled. Nothing was changed.
goto DONE

:FAILED
echo.
echo   The rule was NOT added. netsh reported a failure above.
echo   Nothing was changed. Do not assume the ports are closed.
goto DONE

:DONE
echo.
pause
:EOF
endlocal

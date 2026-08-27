@echo off
REM ============================================================
REM  Trade suggestions to your phone, for YOUR approval.
REM  No exchange link. No API key. Nothing is ever traded.
REM ============================================================
cd /d "%~dp0"
call ".venv\Scripts\activate.bat"

echo.
echo  ===============================================================
echo   PHONE ALERTS SETUP
echo  ===============================================================
echo   1. On your phone, install the app "ntfy" (free, no account)
echo   2. In the app tap + and subscribe to a topic name you invent.
echo      Make it random, e.g.  lawre-cvn-8f3k2q
echo      (anyone who knows the name can read it, so don't use "xrp")
echo   3. Type that SAME name below.
echo  ===============================================================
echo.
set /p TOPIC=Your ntfy topic name:
if "%TOPIC%"=="" (echo No topic entered. & pause & exit /b 1)

echo.
echo Sending a test alert to your phone...
python signal_watch.py --topic %TOPIC% --test-push
echo.
echo If that said DELIVERED and your phone buzzed, press any key to start
echo watching. If not, check the topic name matches the app exactly.
pause

echo.
echo Watching XRP-USD and checking every 15 minutes.
echo Your phone buzzes ONLY when the signal changes.
echo Nothing is ever traded - you decide and place it yourself.
echo Press Ctrl+C to stop.
echo.
python signal_watch.py --symbol XRP-USD --granularity hour --topic %TOPIC% --interval 900
pause

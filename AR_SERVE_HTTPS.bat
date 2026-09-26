@echo off
REM AR_SERVE_HTTPS.bat -- put an HTTPS front on the phone's install door.
REM
REM WHY THIS EXISTS (2026-09-16): /m and /m/apk are served over plain HTTP on
REM port 5000. Chrome on Android refuses to download .apk over a non-HTTPS
REM origin -- the download dies with little or no explanation. The APK itself
REM is fine: verified 45,153,060 bytes, sha256 decbe825..4b9e8, served at
REM 14 MB/s. The transport is the problem, not the build.
REM
REM MEASURED 2026-09-18, and it changes what this script can promise:
REM
REM   1. THE CLI CHANGED. `tailscale serve --bg https / http://127.0.0.1:5000`
REM      is refused outright on 1.102.4 ("the CLI for serve and funnel has
REM      changed"). The form it accepts is `tailscale serve --bg <target>`.
REM      This script used the old syntax and would have failed on every run.
REM
REM   2. THIS TAILNET CANNOT ISSUE A CERT. Asking for one directly:
REM        tailscale cert <tailnet-dns-name>
REM        -> 500 Internal Server Error: your Tailscale account does not
REM           support getting TLS certs
REM      and `tailscale status --json` reports CertDomains: None. So HTTPS is
REM      not one command away -- it needs HTTPS Certificates enabled for the
REM      tailnet first, in the admin console (DNS -> HTTPS Certificates), which
REM      is the ACCOUNT OWNER'S decision and not something a script should make
REM      for him. Until then `serve` can publish over HTTP only, which buys
REM      Chrome nothing.
REM
REM   SO THE ROUTE THAT ACTUALLY WORKS TODAY, in order of least effort:
REM
REM   a. THE APP'S OWN UPDATER. It needs no browser and no cert: the phone asks
REM      the PC's /app/latest on its ten-minute heartbeat, verifies the PC's
REM      signature over the manifest, downloads /app/apk, and hands the file to
REM      Android's installer, which asks you. Proven end to end on 2026-09-18 --
REM      see ops/app/requests.jsonl for the asks it records. Nothing to run here.
REM
REM   b. A NON-CHROME BROWSER on the phone, at the plain door:
REM        http://<pc-tailnet-ip>:5000/m     then tap Install
REM      Firefox and Samsung Internet will download over HTTP; Chrome will not.
REM      The M-ROUTE GATE answers the tailnet only, which is where you are.
REM
REM   c. ENABLE HTTPS CERTIFICATES in the admin console, then run this script.
REM      That is the only path that makes Chrome work.
REM
REM Nothing in the repo changes either way. The M-ROUTE GATE still applies:
REM requests arrive from the tailnet, which is exactly what it already allows.

setlocal
title Covenant -- serve /m over HTTPS

set TS=tailscale
where tailscale >nul 2>&1
if errorlevel 1 (
  if exist "C:\Program Files\Tailscale\tailscale.exe" (
    set TS="C:\Program Files\Tailscale\tailscale.exe"
  ) else (
    echo [x] tailscale.exe is not on PATH and not in C:\Program Files\Tailscale.
    goto :done
  )
)

REM The PC's tailnet name and address are read at run time: this file is public and
REM carries neither (2026-09-26 OPSEC sweep, "protect operation security in all we do by default").
set TSNAME=
set TSIP=
for /f "usebackq tokens=1,2" %%A in (`python -c "import subprocess,json,shutil;e=shutil.which('tailscale') or r'C:\Program Files\Tailscale\tailscale.exe';s=json.loads(subprocess.run([e,'status','--json'],capture_output=True,text=True).stdout)['Self'];print(s['DNSName'].rstrip('.'),[i for i in s['TailscaleIPs'] if '.' in i][0])"`) do (
  set TSNAME=%%A
  set TSIP=%%B
)
if not defined TSNAME (
  echo [x] Could not read this PC's tailnet name from tailscale status.
  goto :done
)

echo [1/4] Tailscale status
%TS% status --self --peers=false
echo.

echo [2/4] Can this tailnet issue a TLS cert at all?
%TS% cert --cert-file NUL --key-file NUL %TSNAME% >nul 2>&1
if errorlevel 1 (
  echo     [x] NO. This is the blocker, and no amount of `serve` gets past it.
  echo         Enable it: Tailscale admin console -^> DNS -^> HTTPS Certificates
  echo         -^> Enable, then run this again.
  echo.
  echo     Meanwhile, the two routes that need no cert:
  echo       - the APP updates itself on its heartbeat; just leave it running
  echo       - or open  http://%TSIP%:5000/m  in FIREFOX or Samsung
  echo         Internet ^(not Chrome^) and tap Install
  goto :done
)
echo     [ok] a cert is available.
echo.

echo [3/4] Publishing https -^> http://127.0.0.1:5000
%TS% serve --bg http://127.0.0.1:5000
if errorlevel 1 (
  echo     ...refused, trying the older syntax for an older client
  %TS% serve --bg https / http://127.0.0.1:5000
)
if errorlevel 1 (
  echo.
  echo [x] serve failed even with a cert available. Read the message above.
  goto :done
)
echo.

echo [4/4] What is published now
%TS% serve status
echo.
echo Open the https URL above on the phone, add /m, and tap Install.
echo.
echo To take it down again:  %TS% serve --https=443 off
echo To clear every serve:   %TS% serve reset

:done
echo.
pause
endlocal

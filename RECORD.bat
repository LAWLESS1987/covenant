@echo off
REM ===========================================================================
REM  RECORD.bat -- one double-click. Gather what was actually said, and
REM  attribute every line of it. 2026-08-31.
REM
REM  It EXTRACTS and ATTRIBUTES. It never summarises, concludes, or fills a
REM  gap -- there is no model call anywhere in the path, so no sentence can
REM  appear that nobody said. That matters because this record may be read one
REM  day by a lawyer or a court, and a record that cannot be separated from its
REM  own paraphrase is a story about evidence rather than evidence.
REM
REM  1. IMPORT  hands a vendor export to import_conversations.py (lossless,
REM             no model call, names every file it could not parse).
REM  2. SEARCH  sweeps every system already readable WITHOUT a login --
REM             Claude Code sessions, the Ollama desktop database, the memory
REM             store -- and prints each passage with its file and timestamp.
REM
REM  Boilerplate is filtered. Searching "hospice" once returned five sessions
REM  and every hit was a healthcare tool description sitting in the system
REM  prompt. A compilation that reported those as evidence would have been
REM  worse than one that found nothing.
REM ===========================================================================
setlocal
cd /d "%~dp0"
title COVENANT -- RECORD
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe
echo.
echo   1  Import a vendor export (ChatGPT / Claude / Gemini / Mistral / DeepSeek)
echo   2  Search every system already on this machine
echo.
set /p WHAT=  Choose 1 or 2:
if "%WHAT%"=="1" goto IMPORT
if "%WHAT%"=="2" goto SEARCH
echo   Nothing chosen. Nothing done.
goto END
:IMPORT
echo.
echo   Drag the export file or folder into this window, then press Enter.
set /p SRC=  export:
"%PY%" compile_record.py --import %SRC%
goto END
:SEARCH
echo.
echo   Terms must ALL appear in a passage. Example:  aunt hospital 2024
set /p TERMS=  terms:
"%PY%" compile_record.py --topic %TERMS% --out RECORD_OUT.md
echo.
echo   Written to RECORD_OUT.md
:END
echo.
pause
endlocal

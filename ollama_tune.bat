@echo off
REM OLLAMA_TUNE.bat -- set the two Ollama variables that decide whether the
REM judge fits, and show what is currently set. Nothing here is applied until
REM you run it with APPLY, so a bare double-click is safe and read-only.
REM
REM WHY. judge_bench.fit_check already records the failure this guards: an
REM oversized model means ggml_aligned_malloc fails, Ollama returns HTTP 500,
REM the judge fails CLOSED, and every transaction is rejected -- scoring 3/6,
REM which "does not look broken, it looks strict". Measured margin on this box
REM (LEAN_MEASURE.txt, 2026-08-22): 15.3 GB total, 5.6 GB free with the model
REM NOT resident. That is not comfortable headroom for an 8b model.
REM
REM   OLLAMA_KEEP_ALIVE      the default unloads after a few minutes idle, so a
REM                          judge that fires irregularly pays a reload on the
REM                          critical path of a consensus gate AND a load-time
REM                          allocation spike exactly when memory is tightest.
REM                          -1 keeps it resident: steady RAM, no spike.
REM                          The bad case is the default, because it is neither
REM                          and it is invisible.
REM   OLLAMA_MAX_LOADED_MODELS=1
REM                          stops a second model becoming resident. At this
REM                          margin one concurrent load is the difference
REM                          between fitting and HTTP 500.
REM
REM num_ctx is NOT set here. covenant_judge_ollama.py pins 2048 deliberately
REM ("the prompt is ~500 tokens; anything larger just allocates KV cache you
REM will never fill") and _check_context refuses a verdict computed on a
REM truncated prompt. Raising it trades correctness for memory. Leave it.

setlocal
echo(
echo === current ===
echo   OLLAMA_KEEP_ALIVE        = %OLLAMA_KEEP_ALIVE%
echo   OLLAMA_MAX_LOADED_MODELS = %OLLAMA_MAX_LOADED_MODELS%
echo   OLLAMA_NUM_PARALLEL      = %OLLAMA_NUM_PARALLEL%
echo(
echo === free memory ===
wmic OS get FreePhysicalMemory,TotalVisibleMemorySize /value 2^>NUL | findstr "="
echo(

if /I not "%~1"=="APPLY" (
  echo Read-only. To set them for your user account, run:
  echo     OLLAMA_TUNE.bat APPLY
  echo Then RESTART Ollama -- it reads these at start, not per request.
  goto :eof
)

setx OLLAMA_KEEP_ALIVE -1 >NUL
setx OLLAMA_MAX_LOADED_MODELS 1 >NUL
echo Set for your user account. They take effect in NEW processes only.
echo RESTART Ollama, then re-run AH_FITCHECK.bat to confirm the model still fits.
endlocal

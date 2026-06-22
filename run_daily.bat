@echo off
REM Daily lead-gen run, launched by Windows Task Scheduler.
REM Runs the pipeline and appends all output to output\run.log with a timestamp.

set "PROJECT=d:\Work\Practice Projects\lead-gen"
set "PY=C:\Python314\python.exe"

cd /d "%PROJECT%"
if not exist "%PROJECT%\output" mkdir "%PROJECT%\output"

echo ============================================================ >> "%PROJECT%\output\run.log"
echo Run started: %DATE% %TIME% >> "%PROJECT%\output\run.log"
"%PY%" main.py >> "%PROJECT%\output\run.log" 2>&1
echo Run finished: %DATE% %TIME% (exit %ERRORLEVEL%) >> "%PROJECT%\output\run.log"

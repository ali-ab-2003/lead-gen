@echo off
REM Daily lead-gen run, launched by Windows Task Scheduler.
REM Runs the pipeline and appends all output to output\run.log with a timestamp.
REM Paths are derived from this script's location, so it works from any folder.

set "PROJECT=%~dp0"
REM strip trailing backslash
if "%PROJECT:~-1%"=="\" set "PROJECT=%PROJECT:~0,-1%"

cd /d "%PROJECT%"
if not exist "%PROJECT%\output" mkdir "%PROJECT%\output"

echo ============================================================ >> "%PROJECT%\output\run.log"
echo Run started: %DATE% %TIME% >> "%PROJECT%\output\run.log"
python main.py >> "%PROJECT%\output\run.log" 2>&1
echo Run finished: %DATE% %TIME% (exit %ERRORLEVEL%) >> "%PROJECT%\output\run.log"

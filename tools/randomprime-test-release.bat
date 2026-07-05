@echo off
cd /D "%~dp0"
cd ..

uv sync --extra gui --extra exporters --group installer --reinstall-package py-randomprime
if %ERRORLEVEL% NEQ 0 goto :error

uv run --no-sync tools/create_release.py
if %ERRORLEVEL% NEQ 0 goto :error

echo Done. Output in dist\
pause
exit /b 0

:error
echo Failed with error %ERRORLEVEL%
pause
exit /b %ERRORLEVEL%

@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found. Opening the offline PDF instead.
  if exist "talks\filtering\output\academic.pdf" (
    start "" "talks\filtering\output\academic.pdf"
  ) else (
    echo Build or export the presentation first. See WINDOWS.md.
    pause
  )
  exit /b 0
)
node "scripts\present.mjs" %*
if errorlevel 1 pause

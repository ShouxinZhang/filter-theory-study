@echo off
setlocal
cd /d "%~dp0"
set "SLIDEV_NODE_ARCH=win-x64"
if /I "%PROCESSOR_ARCHITECTURE%"=="ARM64" set "SLIDEV_NODE_ARCH=win-arm64"
if /I "%PROCESSOR_ARCHITEW6432%"=="ARM64" set "SLIDEV_NODE_ARCH=win-arm64"
if not exist "%~dp0runtime\%SLIDEV_NODE_ARCH%\node.exe" (
  echo The portable runtime is missing. Please extract the COMPLETE ZIP first.
  pause
  exit /b 1
)
"%~dp0runtime\%SLIDEV_NODE_ARCH%\node.exe" "%~dp0scripts\present.mjs"
if errorlevel 1 pause

@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0Stop-SanGuo.ps1"

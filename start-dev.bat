@echo off
setlocal
cd /d "%~dp0"

if exist "%ProgramFiles%\Git\bin\bash.exe" (
  "%ProgramFiles%\Git\bin\bash.exe" -lc "bash ./start-dev.sh"
  exit /b %errorlevel%
)

if exist "%ProgramFiles(x86)%\Git\bin\bash.exe" (
  "%ProgramFiles(x86)%\Git\bin\bash.exe" -lc "bash ./start-dev.sh"
  exit /b %errorlevel%
)

echo ไม่พบ Git Bash ที่ติดตั้งไว้ใน Program Files
echo กรุณาเปิด Git Bash แล้วรัน: bash ./start-dev.sh
pause

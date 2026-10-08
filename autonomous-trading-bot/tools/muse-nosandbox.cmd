@echo off
REM ============================================================================
REM  Muse Code KHONG SANDBOX (--disable-sandbox)
REM
REM  Giai quyet DIEM VAP #2: trong sandbox, .git la READ-ONLY -> Muse khong tu
REM  commit/push duoc. Script nay bo sandbox => .git ghi duoc + full network.
REM
REM  !!! CANH BAO: agent ghi duoc MOI file (ke ca .git, .env) va ra mang tu do.
REM  !!! Uu tien cach an toan: de Muse sua file, roi ban chay tools\git-sync.cmd
REM  !!! Chi dung script nay khi ban da tin workspace va dang theo doi phien.
REM
REM  Vi du:  tools\muse-nosandbox.cmd exec "commit va push giup toi" --max-model-steps 8
REM ============================================================================
setlocal
echo [CANH BAO] Bo sandbox: agent ghi duoc .git/.env va ra mang tu do.
echo            Bam Ctrl+C trong 5 giay neu khong chac chan...
timeout /t 5 /nobreak >nul
set "MUSE_BIN="
for /f "delims=" %%F in ('dir /b /o-d "%LOCALAPPDATA%\Programs\muse\muse-bin-*.exe" 2^>nul') do if not defined MUSE_BIN set "MUSE_BIN=%LOCALAPPDATA%\Programs\muse\%%F"
if not defined MUSE_BIN set "MUSE_BIN=muse"
cd /d "%~dp0.."
REM LUU Y: co Muse phai nam SAU subcommand (xem tools\muse.cmd).
"%MUSE_BIN%" %* --disable-sandbox

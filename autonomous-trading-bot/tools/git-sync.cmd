@echo off
REM ============================================================================
REM  Chay NGOAI sandbox cua Muse: commit + push thay doi trong workspace.
REM
REM  Day la CACH AN TOAN de giai quyet DIEM VAP #2 (.git read-only trong sandbox):
REM  Muse sua file -> script nay commit + push. Khong phai tat sandbox.
REM
REM  Dung:  tools\git-sync.cmd "feat: mo ta thay doi"
REM         (khong truyen message -> dung mac dinh "chore: cap nhat workspace")
REM ============================================================================
setlocal
cd /d "%~dp0.."
set "MSG=%~1"
if "%MSG%"=="" set "MSG=chore: cap nhat workspace"
echo === Trang thai hien tai ===
git status --short
git add -A
git diff --cached --quiet
if not errorlevel 1 (
  echo [i] Khong co thay doi de commit.
  exit /b 0
)
git commit -m "%MSG%"
if errorlevel 1 (
  echo [LOI] commit that bai.
  exit /b 1
)
echo === Push len origin (SSH) ===
git push -u origin HEAD
if errorlevel 1 (
  echo [LOI] push that bai. Kiem tra SSH key da them vao GitHub chua:
  echo      ssh -T git@github.com
  exit /b 1
)
echo === XONG: da commit + push ===

@echo off
REM ============================================================================
REM  Muse Code - chay trong repo nay voi NETWORK DAY DU
REM  (sandbox + approval VAN BAT, chi mo them ket noi ra ngoai)
REM
REM  Giai quyet DIEM VAP #1: mac dinh --sandbox-network=proxy-only nen moi ket noi
REM  toi host/port moi (vd github.com:22) se DUNG XIN PHE DUYET.
REM  Script nay doi sang 'enabled' -> khong bi dung nua, van giu sandbox.
REM
REM  Dung khi: git ls-remote, tai tai lieu, pip install...
REM  Vi du:   tools\muse.cmd exec "chay git ls-remote origin" --max-model-steps 4
REM           tools\muse.cmd          (mo giao dien interactive binh thuong)
REM ============================================================================
setlocal
set "MUSE_BIN="
for /f "delims=" %%F in ('dir /b /o-d "%LOCALAPPDATA%\Programs\muse\muse-bin-*.exe" 2^>nul') do if not defined MUSE_BIN set "MUSE_BIN=%LOCALAPPDATA%\Programs\muse\%%F"
if not defined MUSE_BIN set "MUSE_BIN=muse"
cd /d "%~dp0.."
REM LUU Y: co Muse phai nam SAU subcommand (vd: exec ... --sandbox-network enabled).
REM Dat truoc 'exec' se bi hieu thanh TUI mode -> loi "unexpected argument".
"%MUSE_BIN%" %* --sandbox-network enabled

@echo off
chcp 65001 >nul 2>&1
title Claude Code - Autonomous Setup

echo.
echo ==========================================================
echo   CLAUDE CODE - AUTONOMOUS EXECUTION SETUP
echo   Project: %CD%
echo ==========================================================
echo.

REM Duong dan tuyet doi, backslash da duoc nhan doi de nhet vao JSON
set "PROOT=%CD:\=\\%"
set "S=.claude\settings.json"
set "H=.claude\hooks\stop-guard.bat"

REM ============ 1. TAO THU MUC ============
if not exist ".claude\hooks" mkdir ".claude\hooks"
echo [1/5] Da tao .claude\hooks

REM ============ 2. TAO STOP HOOK ============
> "%H%" (
echo @echo off
echo REM Stop hook: chan Claude Code dung lai cho den khi PROGRESS.md co sentinel
echo set "PF=%%~dp0..\..\PROGRESS.md"
echo findstr /R /C:"^^STATUS: *ALL_MILESTONES_DONE" /C:"^^STATUS: *BLOCKED" "%%PF%%" ^>nul 2^>^&1
echo if %%ERRORLEVEL%% EQU 0 exit /b 0
echo echo {"decision":"block","reason":"PROGRESS.md has no STATUS: ALL_MILESTONES_DONE or STATUS: BLOCKED yet. Read PROGRESS.md, identify the next task and execute it immediately. Do NOT ask the user whether to continue."}
echo exit /b 0
)
echo [2/5] Da tao .claude\hooks\stop-guard.bat

REM ============ 3. TAO SETTINGS.JSON ============
> "%S%" echo {
>>"%S%" echo   "env": {
>>"%S%" echo     "CLAUDE_CODE_STOP_HOOK_BLOCK_CAP": "0"
>>"%S%" echo   },
>>"%S%" echo   "permissions": {
>>"%S%" echo     "defaultMode": "acceptEdits",
>>"%S%" echo     "allow": [
>>"%S%" echo       "Bash(npm run:*)",
>>"%S%" echo       "Bash(npm test:*)",
>>"%S%" echo       "Bash(npx:*)",
>>"%S%" echo       "Bash(pytest:*)",
>>"%S%" echo       "Bash(python:*)",
>>"%S%" echo       "Bash(git add:*)",
>>"%S%" echo       "Bash(git commit:*)",
>>"%S%" echo       "Bash(git status)",
>>"%S%" echo       "Bash(git diff:*)"
>>"%S%" echo     ],
>>"%S%" echo     "deny": [
>>"%S%" echo       "Bash(rm -rf:*)",
>>"%S%" echo       "Bash(sudo:*)",
>>"%S%" echo       "Bash(git push --force:*)",
>>"%S%" echo       "Read(./.env)"
>>"%S%" echo     ]
>>"%S%" echo   },
>>"%S%" echo   "hooks": {
>>"%S%" echo     "Stop": [
>>"%S%" echo       {
>>"%S%" echo         "hooks": [
>>"%S%" echo           {
>>"%S%" echo             "type": "command",
>>"%S%" echo             "command": "\"%PROOT%\\.claude\\hooks\\stop-guard.bat\"",
>>"%S%" echo             "timeout": 15
>>"%S%" echo           }
>>"%S%" echo         ]
>>"%S%" echo       }
>>"%S%" echo     ],
>>"%S%" echo     "SessionStart": [
>>"%S%" echo       {
>>"%S%" echo         "hooks": [
>>"%S%" echo           {
>>"%S%" echo             "type": "command",
>>"%S%" echo             "command": "cmd /c type \"%PROOT%\\PROGRESS.md\" 2^>nul"
>>"%S%" echo           }
>>"%S%" echo         ]
>>"%S%" echo       }
>>"%S%" echo     ]
>>"%S%" echo   }
>>"%S%" echo }
echo [3/5] Da tao .claude\settings.json

REM ============ 4. PROGRESS.MD + SENTINEL ============
if not exist "PROGRESS.md" (
  > "PROGRESS.md" echo STATUS: IN_PROGRESS
  >>"PROGRESS.md" echo.
  >>"PROGRESS.md" echo # PROGRESS
  >>"PROGRESS.md" echo.
  >>"PROGRESS.md" echo ## Milestone / Task da xong
  >>"PROGRESS.md" echo.
  >>"PROGRESS.md" echo ## Task dang lam
  >>"PROGRESS.md" echo.
  >>"PROGRESS.md" echo ## Task ke tiep
  >>"PROGRESS.md" echo.
  >>"PROGRESS.md" echo ## Quyet dinh kien truc
  >>"PROGRESS.md" echo.
  >>"PROGRESS.md" echo ## Trang thai test / coverage
) else (
  findstr /R /C:"^STATUS:" "PROGRESS.md" >nul 2>&1
  if errorlevel 1 (
    > "PROGRESS.tmp" echo STATUS: IN_PROGRESS
    >>"PROGRESS.tmp" echo.
    type "PROGRESS.md" >> "PROGRESS.tmp"
    move /y "PROGRESS.tmp" "PROGRESS.md" >nul
  )
)
echo [4/5] PROGRESS.md san sang

REM ============ 5. THEM QUY TAC SENTINEL VAO CLAUDE.MD ============
findstr /C:"ALL_MILESTONES_DONE" "CLAUDE.md" >nul 2>&1
if errorlevel 1 (
  >>"CLAUDE.md" echo.
  >>"CLAUDE.md" echo ## QUY TAC SENTINEL - BAT BUOC
  >>"CLAUDE.md" echo.
  >>"CLAUDE.md" echo Dong dau tien cua `PROGRESS.md` luon la `STATUS: IN_PROGRESS`.
  >>"CLAUDE.md" echo Chi doi thanh:
  >>"CLAUDE.md" echo - `STATUS: ALL_MILESTONES_DONE` khi da het TOAN BO milestone.
  >>"CLAUDE.md" echo - `STATUS: BLOCKED` khi gap blocker thuc su theo dieu kien dung ^(b^).
  >>"CLAUDE.md" echo.
  >>"CLAUDE.md" echo Ngoai hai truong hop tren, KHONG duoc ket thuc luot de hoi nguoi dung.
)
echo [5/5] Da them quy tac sentinel vao CLAUDE.md

REM ============ CANH BAO HOOK GLOBAL ============
echo.
if exist "%USERPROFILE%\.claude\settings.json" (
  findstr /C:"\"Stop\"" "%USERPROFILE%\.claude\settings.json" >nul 2>&1
  if not errorlevel 1 (
    echo [!] CANH BAO: %USERPROFILE%\.claude\settings.json cung co hook "Stop".
    echo     Settings MERGE chu khong override - ca hai hook se cung chay.
    echo     Hay mo file do va xoa hook Stop di.
    echo.
  )
)

echo ==========================================================
echo   HOAN TAT
echo ==========================================================
echo.
echo Buoc tiep theo:
echo   1. Mo Claude Code trong VS Code tai thu muc nay
echo   2. Go /status - kiem tra .claude\settings.json co trong Setting sources
echo      ^(khong thay = loi cu phap JSON^)
echo   3. Giao 1 task nho de test. Claude se khong tu dung nua.
echo.
echo Muon dung that: sua dong dau PROGRESS.md thanh STATUS: BLOCKED
echo.
echo Nho sua lai muc "allow" trong .claude\settings.json cho khop
echo lenh build/test that cua project nay.
echo.
pause

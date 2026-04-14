@echo off
:: FaceLock — Windows Launcher
:: Usage: run.bat enroll | run.bat start | run.bat auth | run.bat users

set ENV=facelock_env\Scripts\activate.bat

IF "%1"=="enroll" (
    echo [FaceLock] Starting enrollment...
    call %ENV% && python enroll.py --user %2
) ELSE IF "%1"=="start" (
    echo [FaceLock] Starting guardian loop...
    call %ENV% && python facelock.py --user %2
) ELSE IF "%1"=="auth" (
    echo [FaceLock] Starting authentication...
    call %ENV% && python authenticate.py --user %2
) ELSE IF "%1"=="users" (
    echo [FaceLock] Enrolled users:
    call %ENV% && python -c "from modules.database import DatabaseManager; db=DatabaseManager(); print('\n'.join(db.get_all_users()) or 'No users enrolled.')"
) ELSE (
    echo.
    echo  FaceLock — Command Launcher
    echo  ----------------------------
    echo  run.bat enroll [username]   ^| Enroll a face
    echo  run.bat start  [username]   ^| Start guardian loop
    echo  run.bat auth   [username]   ^| Test authentication
    echo  run.bat users               ^| List enrolled users
    echo.
)

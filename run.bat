@echo off
:: FaceLock — Windows Launcher
:: Usage: run.bat <command> [args]

cd /d "%~dp0"
set PY=facelock_env\Scripts\python.exe

IF "%1"=="enroll" (
    echo [FaceLock] Starting enrollment...
    %PY% enroll.py --user %2
) ELSE IF "%1"=="start" (
    echo [FaceLock] Starting guardian loop...
    %PY% facelock.py --user %2
) ELSE IF "%1"=="auth" (
    echo [FaceLock] Starting authentication...
    %PY% authenticate.py --user %2
) ELSE IF "%1"=="users" (
    echo [FaceLock] Enrolled users:
    %PY% -c "import sys; sys.path.insert(0,'.'); from infrastructure.repositories import SQLiteUserRepository; r=SQLiteUserRepository(); users=r.find_all(); print('\n'.join(f'{u.user_id} ({u.role.value})' for u in users) or 'No users enrolled.')"
) ELSE IF "%1"=="eval" (
    echo [FaceLock] Starting biometric evaluation...
    %PY% evaluation/evaluate.py --user %2 %3 %4 %5
) ELSE IF "%1"=="oversight" (
    echo [FaceLock] Human oversight dashboard...
    %PY% oversight/dashboard.py %2 %3
) ELSE IF "%1"=="migrate" (
    echo [FaceLock] Migrating key from Fernet to AES-256-GCM...
    %PY% migrate_key.py
) ELSE IF "%1"=="test" (
    echo [FaceLock] Running test suite...
    %PY% -m pytest tests/ -v %2 %3 %4
) ELSE (
    echo.
    echo  FaceLock — Command Launcher
    echo  -----------------------------------------------
    echo  run.bat enroll    [username]        Enroll a face
    echo  run.bat start     [username]        Start guardian loop
    echo  run.bat auth      [username]        Test authentication
    echo  run.bat users                       List enrolled users
    echo  run.bat eval      [username]        FAR/FRR/EER evaluation
    echo  run.bat oversight [--verify/--lock] Human oversight dashboard
    echo  run.bat migrate                     Upgrade key to AES-256-GCM
    echo  run.bat test                        Run full test suite
    echo.
)

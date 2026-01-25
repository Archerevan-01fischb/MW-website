@echo off
REM ============================================================================
REM Run Database Migration with Backup (Windows)
REM ============================================================================

setlocal enabledelayedexpansion

set DB_PATH=..\settlements.db
set MIGRATION_FILE=001_fix_gondola_naming.sql

REM Generate timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set BACKUP_PATH=..\backups\settlements_backup_%datetime:~0,8%_%datetime:~8,6%.db

echo ================================
echo Database Migration: Fix Gondola Naming
echo ================================
echo.

REM Create backup directory
if not exist ..\backups mkdir ..\backups

REM Step 1: Backup
echo Step 1: Creating backup...
copy "%DB_PATH%" "%BACKUP_PATH%" > nul
echo. Backup created: %BACKUP_PATH%
echo.

REM Step 2: Show current state
echo Step 2: Current gondola system IDs (sample):
sqlite3 "%DB_PATH%" "SELECT DISTINCT gondola_system_id, COUNT(*) as count FROM settlements WHERE gondola_system_id IS NOT NULL GROUP BY gondola_system_id ORDER BY gondola_system_id LIMIT 5;"
echo.

REM Step 3: Run migration
echo Step 3: Running migration...
sqlite3 "%DB_PATH%" < "%MIGRATION_FILE%"
echo. Migration complete
echo.

REM Step 4: Verify
echo Step 4: Verification - New gondola system IDs (sample):
sqlite3 "%DB_PATH%" "SELECT DISTINCT gondola_system_text, COUNT(*) as count FROM settlements WHERE gondola_system_text IS NOT NULL GROUP BY gondola_system_text ORDER BY gondola_system_text LIMIT 5;"
echo.

REM Step 5: Sample new naming
echo Step 5: Sample new naming (GONDOLA_01):
sqlite3 "%DB_PATH%" "SELECT system_name, tile_id, gondola_role FROM settlements WHERE gondola_system_text = 'GONDOLA_01' ORDER BY gondola_sequence;"
echo.

echo ================================
echo. Migration complete!
echo ================================
echo.
echo Backup saved to: %BACKUP_PATH%
echo.
echo To rollback:
echo   copy "%BACKUP_PATH%" "%DB_PATH%"
echo.

pause

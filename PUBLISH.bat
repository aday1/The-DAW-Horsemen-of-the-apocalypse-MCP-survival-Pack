@echo off
setlocal
REM ============================================================
REM  DAW HORSEMEN - PUBLISH (dev box only)
REM  Pushes committed work to GitHub. Commits are human-approved:
REM  commit first (or let your agent prepare the commit), then run me.
REM ============================================================
cd /d "%~dp0"
echo  == THE DAW HORSEMEN - PUBLISH == > publish_log.txt
git status --short >> publish_log.txt 2>&1
git log origin/main..HEAD --oneline >> publish_log.txt 2>&1
echo  Pushing to origin main... >> publish_log.txt
git push origin main >> publish_log.txt 2>&1
if errorlevel 1 (
  echo  PUSH FAILED - see publish_log.txt
  echo  RESULT=FAIL >> publish_log.txt
) else (
  echo  Pushed. GitHub is up to date.
  echo  RESULT=OK >> publish_log.txt
)
type publish_log.txt
pause

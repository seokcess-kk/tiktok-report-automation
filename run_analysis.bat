@echo off
REM TikTok Ad Analysis Automation - Windows Batch Runner
REM Phase 3: Full Automation

echo ============================================================
echo TikTok Ad Analysis - Phase 3 Full Automation
echo ============================================================

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.8+
    exit /b 1
)

REM Check input file
if not exist "input\tiktok_raw.csv" (
    echo [ERROR] Input file not found: input\tiktok_raw.csv
    exit /b 1
)

echo [OK] Input file found

REM Optional files check
if exist "input\creative_lineage.csv" (
    echo [INFO] creative_lineage.csv detected - lineage matching enabled
)
if exist "input\db_by_branch.csv" (
    echo [INFO] db_by_branch.csv detected - funnel analysis enabled
)
if exist "input\target_cpa.csv" (
    echo [INFO] target_cpa.csv detected - custom CPA thresholds enabled
)

echo.
echo Starting analysis...
echo.

REM Run analysis
python run_analysis.py

if errorlevel 1 (
    echo [ERROR] Analysis failed
    exit /b 1
)

echo.
echo ============================================================
echo Analysis completed successfully!
echo ============================================================
pause

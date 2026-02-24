@echo off
REM Batch script to set environment variables for Airspace Copilot
REM Run this script: env_setup.bat

REM Webhook URL for region1 (default: http://localhost:5678/webhook/latest-region1)
set REGION1_WEBHOOK=http://localhost:5678/webhook/latest-region1

REM Groq API Key (required for agents.py)
REM Replace with your actual API key
set GROQ_API_KEY=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

echo Environment variables set for current session:
echo   REGION1_WEBHOOK = %REGION1_WEBHOOK%
if defined GROQ_API_KEY (
    echo   GROQ_API_KEY = ***SET***
) else (
    echo   GROQ_API_KEY = NOT SET
)
echo.
echo Note: These are set for the current command prompt session only.
echo To set permanently, use: setx REGION1_WEBHOOK "value"


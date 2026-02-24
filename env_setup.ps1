# PowerShell script to set environment variables for Airspace Copilot
# Run this script in PowerShell: .\env_setup.ps1

# Webhook URL for region1 (default: http://localhost:5678/webhook/latest-region1)
$env:REGION1_WEBHOOK = "http://localhost:5678/webhook/latest-region1"

# Groq API Key (required for agents.py)
# Replace with your actual API key
$env:GROQ_API_KEY = "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"

Write-Host "Environment variables set for current session:"
Write-Host "  REGION1_WEBHOOK = $env:REGION1_WEBHOOK"
Write-Host "  GROQ_API_KEY = $(if ($env:GROQ_API_KEY) { '***SET***' } else { 'NOT SET' })"
Write-Host ""
Write-Host "Note: These are set for the current PowerShell session only."
Write-Host "To set permanently, use: [System.Environment]::SetEnvironmentVariable('REGION1_WEBHOOK', 'value', 'User')"


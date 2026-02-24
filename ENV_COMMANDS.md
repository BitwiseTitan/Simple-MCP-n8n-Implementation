# Environment Variables Setup

This project uses the following environment variables:

## Required Environment Variables

### 1. `GROQ_API_KEY`
- **Used in**: `agents.py`
- **Description**: API key for Groq client
- **Required**: Yes (for agents functionality)

### 2. `REGION1_WEBHOOK`
- **Used in**: `server.py`
- **Description**: Webhook URL for region1 flight data
- **Default**: `http://localhost:5678/webhook/latest-region1`
- **Required**: No (has default value)

## PowerShell Commands (Current Session)

```powershell
# Set REGION1_WEBHOOK
$env:REGION1_WEBHOOK = "http://localhost:5678/webhook/latest-region1"

# Set GROQ_API_KEY
$env:GROQ_API_KEY = "your-groq-api-key-here"

# View current values
$env:REGION1_WEBHOOK
$env:GROQ_API_KEY
```

## PowerShell Commands (Permanent - User Level)

```powershell
# Set permanently for current user
[System.Environment]::SetEnvironmentVariable('REGION1_WEBHOOK', 'http://localhost:5678/webhook/latest-region1', 'User')
[System.Environment]::SetEnvironmentVariable('GROQ_API_KEY', 'your-groq-api-key-here', 'User')
```

## Command Prompt (CMD) Commands (Current Session)

```cmd
REM Set REGION1_WEBHOOK
set REGION1_WEBHOOK=http://localhost:5678/webhook/latest-region1

REM Set GROQ_API_KEY
set GROQ_API_KEY=your-groq-api-key-here

REM View current values
echo %REGION1_WEBHOOK%
echo %GROQ_API_KEY%
```

## Command Prompt (CMD) Commands (Permanent - User Level)

```cmd
REM Set permanently for current user
setx REGION1_WEBHOOK "http://localhost:5678/webhook/latest-region1"
setx GROQ_API_KEY "your-groq-api-key-here"
```

## Quick Setup Scripts

### PowerShell
```powershell
.\env_setup.ps1
```

### Command Prompt
```cmd
env_setup.bat
```

## View All Environment Variables

### PowerShell
```powershell
Get-ChildItem Env: | Where-Object { $_.Name -like "*REGION*" -or $_.Name -like "*GROQ*" }
```

### Command Prompt
```cmd
set | findstr /i "REGION GROQ"
```

## Notes

- Environment variables set with `$env:` (PowerShell) or `set` (CMD) are only available in the current session
- To make them permanent, use `[System.Environment]::SetEnvironmentVariable()` (PowerShell) or `setx` (CMD)
- After setting permanent variables, you may need to restart your terminal/IDE for changes to take effect


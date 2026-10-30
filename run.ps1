# LoanLens Launcher PowerShell Script
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=====================================================================" -ForegroundColor Cyan
Write-Host "  LoanLens - Real-Time Voice Loan Assistant Launcher" -ForegroundColor Cyan
Write-Host "=====================================================================" -ForegroundColor Cyan

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvValid = $false

if (Test-Path $venvPython) {
    try {
        & $venvPython -c "import sys" 2>$null
        if ($LASTEXITCODE -eq 0) { $venvValid = $true }
    } catch {
        $venvValid = $false
    }
}

if ($venvValid) {
    Write-Host "[LoanLens] Using project virtual environment in .venv..." -ForegroundColor Green
    & $venvPython launcher.py @args
} else {
    Write-Host "[LoanLens] Using system Python..." -ForegroundColor Green
    python launcher.py @args
}

# Run unit and smoke tests for the Apple OCR Backend

# Ensure we're in the project root
$projectRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $projectRoot

# Activate virtual environment if it exists
$venvPath = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $venvPath
}

# Function to run tests and check exit code
function Run-Test {
    param (
        [string]$TestType,
        [string]$Command
    )
    
    Write-Host "`n=== Running $TestType Tests ===" -ForegroundColor Cyan
    
    try {
        Invoke-Expression $Command
        $exitCode = $LASTEXITCODE
        
        if ($exitCode -eq 0) {
            Write-Host "$TestType tests passed!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "$TestType tests failed with exit code $exitCode" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "Error running $TestType tests: $_" -ForegroundColor Red
        return $false
    }
}

# Check if the API is running
$apiRunning = $false
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($response.StatusCode -eq 200) {
        $apiRunning = $true
        Write-Host "API is running" -ForegroundColor Green
    }
} catch {
    Write-Host "API is not running. Smoke tests will be skipped." -ForegroundColor Yellow
}

# Run unit tests
$unitTestsPassed = Run-Test "Unit" "python -m unittest discover -s tests/unit"

# Run smoke tests if API is running
$smokeTestsPassed = $true
if ($apiRunning) {
    $smokeTestsPassed = Run-Test "Smoke" "python tests/smoke/test_api_endpoints.py"
} else {
    Write-Host "`n=== Skipping Smoke Tests (API not running) ===" -ForegroundColor Yellow
}

# Print summary
Write-Host "`n=== Test Summary ===" -ForegroundColor Cyan
Write-Host "Unit Tests: $(if ($unitTestsPassed) { "PASSED" } else { "FAILED" })" -ForegroundColor $(if ($unitTestsPassed) { "Green" } else { "Red" })
Write-Host "Smoke Tests: $(if ($apiRunning) { if ($smokeTestsPassed) { "PASSED" } else { "FAILED" } } else { "SKIPPED" })" -ForegroundColor $(if ($apiRunning) { if ($smokeTestsPassed) { "Green" } else { "Red" } } else { "Yellow" })

# Exit with appropriate code
if ($unitTestsPassed -and ($smokeTestsPassed -or -not $apiRunning)) {
    Write-Host "`nAll tests completed successfully!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`nSome tests failed!" -ForegroundColor Red
    exit 1
}

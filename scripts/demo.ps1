# Apple Serial OCR Demo Script
# This script demonstrates the key features of the Apple Serial OCR system

# Ensure we're in the project root
$projectRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $projectRoot

# Activate virtual environment if it exists
$venvPath = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "Activating virtual environment..." -ForegroundColor Cyan
    & $venvPath
}

# Function to display section headers
function Show-Section {
    param (
        [string]$Title
    )
    
    Write-Host "`n`n===== $Title =====" -ForegroundColor Magenta
}

# Function to run a curl command and display the result
function Run-Demo {
    param (
        [string]$Title,
        [string]$Command,
        [switch]$ParseJson = $true
    )
    
    Write-Host "`n>> $Title" -ForegroundColor Cyan
    Write-Host "Command: $Command" -ForegroundColor Gray
    
    try {
        $result = Invoke-Expression $Command
        
        if ($ParseJson) {
            try {
                $jsonResult = $result | ConvertFrom-Json | ConvertTo-Json -Depth 4
                Write-Host "Result:" -ForegroundColor Green
                Write-Host $jsonResult
            } catch {
                Write-Host "Result:" -ForegroundColor Yellow
                Write-Host $result
            }
        } else {
            Write-Host "Command executed successfully" -ForegroundColor Green
        }
    } catch {
        Write-Host "Error executing command: $_" -ForegroundColor Red
    }
    
    # Pause for user to see the result
    Write-Host "Press any key to continue..." -ForegroundColor Gray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
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
    Write-Host "API is not running. Please start the API with:" -ForegroundColor Red
    Write-Host "python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor Yellow
    exit 1
}

# Start the demo
Clear-Host
Write-Host "Apple Serial OCR Demo" -ForegroundColor Cyan
Write-Host "=====================" -ForegroundColor Cyan
Write-Host "This script will demonstrate the key features of the Apple Serial OCR system."
Write-Host "Press any key to start the demo..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 1. Check API Health
Show-Section "API Health Check"
Run-Demo "Check API health and GPU status" 'curl.exe "http://localhost:8000/health"'

# 2. Basic OCR
Show-Section "Basic OCR"
Run-Demo "Process a sample image with default settings" 'curl.exe -F "image=@samples/serial_1.jpeg" "http://localhost:8000/process-serial?preset=default"'

# 3. Different Presets
Show-Section "Device Presets"
Run-Demo "List available parameter presets" 'curl.exe "http://localhost:8000/params"'
Run-Demo "Process with 'etched' preset (for MacBook)" 'curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched"'
Run-Demo "Process with 'sticker' preset (for accessories)" 'curl.exe -F "image=@Apple serial/IMG-20250813-WA0034.jpg" "http://localhost:8000/process-serial?preset=sticker"'

# 4. Advanced Features
Show-Section "Advanced Features"
Run-Demo "Process with keyword-guided cropping" 'curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched&keyword_crop=true"'
Run-Demo "Process with horizontal strip zooming" 'curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched&zoom_strips=3"'
Run-Demo "Process with fine-grained rotations" 'curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched&fine_rotation=true"'

# 5. Accuracy Evaluation
Show-Section "Accuracy Evaluation"
Run-Demo "Evaluate accuracy on synthetic dataset" 'curl.exe -G "http://localhost:8000/evaluate" --data-urlencode "dir=exported-assets" --data-urlencode "preset=default"'
Run-Demo "Evaluate accuracy on real-world dataset" 'curl.exe -G "http://localhost:8000/evaluate" --data-urlencode "dir=Apple serial" --data-urlencode "preset=etched"'

# 6. Parameter Optimization
Show-Section "Parameter Optimization"
Run-Demo "Trigger parameter sweep for 'etched' preset" 'curl.exe -X POST "http://localhost:8000/params/sweep?preset=etched&images_dir=exported-assets&labels_file=exported-assets/labels.csv"'

# 7. Export
Show-Section "Export"
Run-Demo "Export serial numbers to Excel" 'curl.exe -o "exports/demo_export.xlsx" "http://localhost:8000/export"' -ParseJson:$false

# Demo complete
Show-Section "Demo Complete"
Write-Host "The demo has completed successfully!" -ForegroundColor Green
Write-Host "For more information, see the documentation in the docs/ directory."
Write-Host "  - DEMO_GUIDE.md: Detailed guide for demonstrating the system"
Write-Host "  - FRONTEND_ROI_GUIDE.md: Guide for integrating with iOS frontend"
Write-Host "  - PROJECT_CONTEXT.md: Overview of the project architecture and goals"

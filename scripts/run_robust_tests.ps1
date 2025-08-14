# Run robust tests on sample images with different presets

# Create exports directory if it doesn't exist
$exportsDir = "exports/debug"
if (-not (Test-Path $exportsDir)) {
    New-Item -Path $exportsDir -ItemType Directory -Force
}

# Test with etched-dark preset
Write-Host "`n`n========== Testing with etched-dark preset ==========" -ForegroundColor Green
python scripts/robust_test.py --image "Apple serial/IMG-20250813-WA0024.jpg" --preset etched-dark

# Test with etched preset
Write-Host "`n`n========== Testing with etched preset ==========" -ForegroundColor Green
python scripts/robust_test.py --image "Apple serial/IMG-20250813-WA0025.jpg" --preset etched

# Test with sticker preset
Write-Host "`n`n========== Testing with sticker preset ==========" -ForegroundColor Green
python scripts/robust_test.py --image "Apple serial/IMG-20250813-WA0026.jpg" --preset sticker

# Test with screen preset
Write-Host "`n`n========== Testing with screen preset ==========" -ForegroundColor Green
python scripts/robust_test.py --image "Apple serial/IMG-20250813-WA0027.jpg" --preset screen

# Test with default preset
Write-Host "`n`n========== Testing with default preset ==========" -ForegroundColor Green
python scripts/robust_test.py --image "Apple serial/IMG-20250813-WA0028.jpg" --preset default

Write-Host "`n`nAll robust tests complete. Check the exports/debug directory for debug images." -ForegroundColor Cyan

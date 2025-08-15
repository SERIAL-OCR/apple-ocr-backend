# Run direct test on Apple serial images without using the API

Write-Host "`n========== Testing Apple Serial OCR Directly ==========" -ForegroundColor Green

# Run the direct test
python scripts/test_apple_serials_direct.py

Write-Host "`nTest complete. Results saved to reports/apple_serials_direct_results.csv" -ForegroundColor Green
Write-Host "Debug images saved to exports/debug/apple_serials_direct" -ForegroundColor Green

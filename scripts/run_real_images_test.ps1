# Run test on real Apple serial images directly without using the API

Write-Host "`n========== Testing Real Apple Serial Images Directly ==========" -ForegroundColor Green

# Run the direct test
python scripts/test_real_images_direct.py

Write-Host "`nTest complete. Results saved to reports/real_images_direct_results.csv" -ForegroundColor Green
Write-Host "Debug images saved to exports/debug/real_images_direct" -ForegroundColor Green

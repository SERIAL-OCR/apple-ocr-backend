# Train and evaluate the complete OCR pipeline with YOLO ROI detection

# Step 1: Install required dependencies
Write-Host "Installing required dependencies..."
pip install -r requirements.txt

# Check if installation was successful
if ($LASTEXITCODE -ne 0) {
    Write-Host "Warning: Some dependencies failed to install. Continuing with available packages..."
}

# Step 2: Prepare dataset for YOLO training
Write-Host "Preparing dataset for YOLO training..."
python scripts/prepare_yolo_dataset.py --input_dirs "Apple serial" "exports/debug_images" --output_dir "data/serial_detector"

# Create model directory if it doesn't exist (for fallback)
$modelDir = "models/serial_detector"
if (-not (Test-Path $modelDir)) {
    New-Item -Path $modelDir -ItemType Directory -Force
}

# Step 3: Train YOLO model
Write-Host "Training YOLO model..."
python scripts/train_yolo_model.py --data data/serial_detector/data.yaml --epochs 30 --batch 16 --skip-on-error

# Step 4: Run evaluation with YOLO ROI detection
Write-Host "Running evaluation with YOLO ROI detection..."
python scripts/run_accuracy_eval.py "Apple serial" --save-debug

# Step 5: Compare with and without YOLO ROI detection
Write-Host "Running comparison evaluation..."
python scripts/run_accuracy_eval.py "Apple serial" --all-presets --save-debug

Write-Host "Training and evaluation complete!"
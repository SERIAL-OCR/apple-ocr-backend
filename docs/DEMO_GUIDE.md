# Apple Serial OCR Demo Guide

This guide provides instructions for demonstrating the Apple Serial OCR system to stakeholders during the Day 4 handoff.

## Setup Instructions

Before the demo, ensure the following:

1. **Environment Setup**:
   - Python 3.11 is installed
   - Virtual environment is activated: `.venv\Scripts\Activate.ps1` (Windows) or `source .venv/bin/activate` (Linux/Mac)
   - Dependencies are installed: `pip install -r requirements.txt`

2. **Data Preparation**:
   - Sample images are available in `samples/` directory
   - Real-world test images are in `Apple serial/` directory
   - `exported-assets/` contains synthetic images with `labels.csv` for accuracy evaluation

3. **API Running**:
   - Start the API server: `python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
   - Verify it's running by accessing `http://localhost:8000/health` in a browser

## Demo Workflow

### 1. Introduction (5 minutes)

- Explain the project goals: Accurate OCR for Apple serial numbers
- Highlight the challenges: Varied formats, glare, low contrast, small text
- Show the architecture diagram (if available)

### 2. Basic OCR Demo (10 minutes)

Run the following commands to demonstrate basic OCR functionality:

```powershell
# Run the smoke test script to demonstrate basic functionality
python tests/smoke/test_api_endpoints.py

# Process a single image with default settings
curl.exe -F "image=@samples/serial_1.jpeg" "http://localhost:8000/process-serial?preset=default"
```

Explain the output:
- Serial numbers detected
- Confidence scores
- Debug image paths

### 3. Advanced Features Demo (15 minutes)

Demonstrate the following advanced features:

**Parameter Presets**:
```powershell
# Show available presets
curl.exe "http://localhost:8000/params"

# Process an image with different presets
curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched"
curl.exe -F "image=@Apple serial/IMG-20250813-WA0034.jpg" "http://localhost:8000/process-serial?preset=sticker"
```

**ROI and Keyword Detection**:
```powershell
# Process with keyword-guided cropping
curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched&keyword_crop=true"

# Process with horizontal strip zooming
curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched&zoom_strips=3"
```

**GPU Acceleration** (if available):
```powershell
# Check GPU status
curl.exe "http://localhost:8000/health"

# Process with fine-grained rotations (GPU accelerated)
curl.exe -F "image=@Apple serial/IMG-20250813-WA0039.jpg" "http://localhost:8000/process-serial?preset=etched&fine_rotation=true"
```

### 4. Accuracy Evaluation (10 minutes)

Run the evaluation script to demonstrate accuracy metrics:

```powershell
# Run evaluation on synthetic dataset
curl.exe -G "http://localhost:8000/evaluate" --data-urlencode "dir=exported-assets" --data-urlencode "preset=default"

# Run evaluation on real-world dataset
curl.exe -G "http://localhost:8000/evaluate" --data-urlencode "dir=Apple serial" --data-urlencode "preset=etched"
```

Show and explain:
- Overall accuracy percentage
- CSV report with per-image results
- Common failure cases and how to address them

### 5. Parameter Optimization (5 minutes)

Demonstrate the parameter sweep functionality:

```powershell
# Trigger a parameter sweep for the 'etched' preset
curl.exe -X POST "http://localhost:8000/params/sweep?preset=etched&images_dir=exported-assets&labels_file=exported-assets/labels.csv"

# Show the optimized parameters after sweep completes
curl.exe "http://localhost:8000/params?preset=etched"
```

### 6. Frontend Integration (5 minutes)

- Show the `docs/FRONTEND_ROI_GUIDE.md` document
- Explain how the iOS frontend will integrate with the backend
- Demonstrate the `preset` parameter for different device types

### 7. Q&A (10 minutes)

- Address any questions about the implementation
- Discuss next steps and future enhancements

## Key Talking Points

During the demo, highlight these key achievements:

1. **Accuracy Improvements**:
   - Preprocessing pipeline with CLAHE, bilateral filtering, and adaptive thresholding
   - Test-time augmentation with rotations
   - ROI detection and keyword-guided cropping
   - Glare reduction techniques
   - Ambiguous character handling

2. **Performance Optimizations**:
   - GPU acceleration
   - Parameter caching
   - Preset-based configuration

3. **Developer Experience**:
   - Comprehensive API documentation
   - Structured logging
   - Unit and smoke tests
   - Parameter sweep automation

4. **Future Enhancements**:
   - Further accuracy improvements
   - Integration with Apple validation API
   - Mobile-optimized preprocessing
   - Additional device presets

## Troubleshooting

If you encounter issues during the demo:

- **API not responding**: Check if the server is running and the port is correct
- **Low accuracy**: Try different presets or manually adjust parameters
- **GPU errors**: Set `FORCE_CPU=1` environment variable to fall back to CPU processing
- **Image errors**: Ensure the image paths are correct and the files exist

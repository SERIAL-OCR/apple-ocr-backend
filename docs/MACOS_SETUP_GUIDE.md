# macOS Setup Guide for Apple OCR Backend

This guide provides detailed instructions for setting up and running the Apple OCR Backend on macOS, including GPU acceleration configuration.

## System Requirements

- macOS 10.15 (Catalina) or newer
- Python 3.11 (recommended) or 3.10
- At least 8GB RAM (16GB+ recommended)
- For GPU acceleration: 
  - Apple Silicon (M1/M2/M3) Mac, or
  - Intel Mac with compatible AMD GPU

## Installation Steps

### 1. Install Python 3.11

There are several ways to install Python on macOS:

**Option A: Using Homebrew (recommended)**

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.11
brew install python@3.11

# Verify installation
python3.11 --version
```

**Option B: Using the official installer**

1. Download the latest Python 3.11 installer from [python.org](https://www.python.org/downloads/macos/)
2. Run the installer package and follow the instructions
3. Verify installation by opening Terminal and running `python3.11 --version`

### 2. Clone the Repository

```bash
# Clone the repository
git clone https://github.com/your-org/apple-ocr-backend.git
cd apple-ocr-backend
```

### 3. Create and Activate Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate
```

### 4. Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

## GPU Acceleration Setup

### For Apple Silicon Macs (M1/M2/M3)

Apple Silicon Macs can use MPS (Metal Performance Shaders) backend for PyTorch, which provides GPU acceleration.

```bash
# Install PyTorch with MPS support
pip uninstall torch torchvision
pip install torch torchvision
```

To verify MPS is available:

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"MPS available: {torch.backends.mps.is_available()}")
print(f"MPS built: {torch.backends.mps.is_built()}")
```

#### Configure the Application for MPS

Edit `app/config.py` to add MPS support:

```python
# Auto-detect GPU availability for EasyOCR (allow override via env)
try:
    import torch  # type: ignore
    force_cpu = os.getenv("FORCE_CPU", "").strip() in {"1", "true", "TRUE", "yes", "YES"}
    
    # Check for CUDA (NVIDIA) or MPS (Apple Silicon)
    _HAS_CUDA = bool(getattr(torch, "cuda", None) and torch.cuda.is_available())
    _HAS_MPS = bool(getattr(torch.backends, "mps", None) and 
                   torch.backends.mps.is_available() and 
                   torch.backends.mps.is_built())
    
    _USE_GPU = (not force_cpu) and (_HAS_CUDA or _HAS_MPS)
    _GPU_TYPE = "cuda" if _HAS_CUDA else "mps" if _HAS_MPS else "cpu"
except Exception:
    _USE_GPU = False
    _GPU_TYPE = "cpu"
```

### For Intel Macs with AMD GPUs

Intel Macs with AMD GPUs don't have native PyTorch GPU support. For these systems:

1. Use CPU mode by setting the environment variable `FORCE_CPU=1`
2. Consider using external GPU acceleration solutions like PlaidML (requires additional setup)

## Running the Application

### Start the API Server

```bash
# Activate virtual environment if not already activated
source .venv/bin/activate

# Start the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify GPU Usage

1. Access the health endpoint: http://localhost:8000/health
2. Check the GPU information in the response

### Environment Variables

- `FORCE_CPU=1`: Force CPU mode even if GPU is available
- `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`: Prevent MPS from reserving too much memory
- `OCR_BATCH_SIZE=4`: Control batch size for EasyOCR (reduce if experiencing memory issues)

## Performance Considerations for macOS

### Apple Silicon (M1/M2/M3)

- **Memory Management**: MPS backend can use a lot of memory. If you experience out-of-memory issues:
  - Set `PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`
  - Reduce batch size with `OCR_BATCH_SIZE=2` environment variable
  - Process smaller images or reduce upscale factor

- **First-Run Performance**: The first OCR operation might be slow due to shader compilation. Subsequent operations will be faster.

### Intel Macs

- **CPU Mode Optimization**: When running in CPU mode:
  - Reduce the number of rotations tried
  - Use smaller upscale factors (2.0 instead of 4.0)
  - Disable fine-grained rotations

## Troubleshooting

### Common Issues

1. **"MPS not available" error**
   - Ensure you're using macOS 12.3 or newer
   - Verify PyTorch version 1.12 or newer
   - Try reinstalling PyTorch: `pip install --force-reinstall torch torchvision`

2. **Memory errors with MPS**
   - Add environment variable: `export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`
   - Reduce batch size: `export OCR_BATCH_SIZE=1`
   - Process with smaller upscale factor: `upscale_scale=2.0`

3. **Slow performance**
   - First run is always slower due to compilation
   - Try disabling fine rotations for faster processing
   - Use the `etched` preset which is optimized for Apple hardware

4. **Installation errors with OpenCV**
   - Install using Homebrew: `brew install opencv`
   - Then install Python binding: `pip install opencv-python`

### Checking Logs

Log files are stored in the `logs/` directory. Check these files for detailed error information:

```bash
# View the last 50 lines of the structured log
tail -n 50 logs/ocr_structured.jsonl
```

## Testing the Installation

### Run Unit Tests

```bash
# Run all unit tests
python -m unittest discover -s tests/unit

# Run specific test file
python -m unittest tests/unit/utils/test_validation.py
```

### Run Smoke Tests

```bash
# Ensure the API is running, then:
python tests/smoke/test_api_endpoints.py
```

### Process a Test Image

```bash
# Process a single image with curl
curl -F "image=@samples/serial_1.jpeg" "http://localhost:8000/process-serial?preset=default"
```

## Additional macOS-Specific Tools

### GPU Monitoring

To monitor GPU usage on Apple Silicon:

```bash
# Install Activity Monitor CLI
brew install osx-cpu-temp

# Monitor system resources including GPU
sudo powermetrics --samplers gpu_power
```

### Performance Profiling

For detailed performance analysis:

```bash
# Install py-spy
pip install py-spy

# Generate CPU flame graph
py-spy record -o profile.svg --pid <PID_OF_UVICORN>
```

## Conclusion

This setup should provide a functional Apple OCR Backend on macOS with GPU acceleration for Apple Silicon Macs. For optimal performance, consider the device-specific recommendations and troubleshooting steps provided above.

For further assistance, please refer to the project documentation or open an issue on the project repository.

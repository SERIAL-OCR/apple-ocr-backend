# GPU Acceleration Setup Guide

## Overview
EasyOCR can leverage GPU acceleration via PyTorch CUDA to significantly improve OCR processing speed. While GPU doesn't directly increase accuracy, it enables more aggressive preprocessing and multiple detection passes without latency penalties.

## Benefits of GPU Acceleration

### Performance Improvements
- **5-10x faster** text detection and recognition
- Enables real-time processing (<100ms per image)
- Allows multiple passes (rotations, inversions) without timeout
- Supports batch processing efficiently

### Accuracy Benefits (Indirect)
- Can afford higher upscaling (4x-5x) without timeout
- Multiple rotation angles (0°, 90°, 180°, 270°, ±15°, ±30°)
- More preprocessing variations in parallel
- Deeper neural network models for better recognition

## Installation

### 1. Check CUDA Compatibility

First, check if you have an NVIDIA GPU:
```bash
# Windows
wmic path win32_VideoController get name

# Linux
lspci | grep -i nvidia

# Check CUDA version (if installed)
nvidia-smi
```

### 2. Install CUDA Toolkit

Download and install CUDA Toolkit (11.8 or 12.1 recommended):
- [CUDA Toolkit Downloads](https://developer.nvidia.com/cuda-downloads)

### 3. Install PyTorch with CUDA

```bash
# For CUDA 11.8
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# For CPU only (fallback)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 4. Verify Installation

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU count: {torch.cuda.device_count()}")
if torch.cuda.is_available():
    print(f"GPU name: {torch.cuda.get_device_name(0)}")
```

## Configuration

### Enable GPU in Application

Update `app/config.py`:
```python
import torch

OCR_SETTINGS = {
    "languages": ["en"],
    "use_gpu": torch.cuda.is_available(),  # Auto-detect GPU
    # Or force GPU usage:
    # "use_gpu": True,
}
```

### Docker Setup with GPU

#### Dockerfile.gpu
```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python 3.11
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install PyTorch with CUDA
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### docker-compose.gpu.yml
```yaml
version: '3.8'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile.gpu
    ports:
      - "8000:8000"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
```

Run with GPU:
```bash
# Requires nvidia-docker2 package
docker-compose -f docker-compose.gpu.yml up
```

## Performance Tuning

### 1. Memory Management

```python
# In app/pipeline/ocr_adapter.py
import torch

def cleanup_gpu():
    """Free GPU memory after processing."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        
# Call after each request in production
```

### 2. Batch Processing

```python
def process_batch(images: List[bytes]) -> List[List[Tuple[str, float]]]:
    """Process multiple images in a single GPU batch."""
    reader = _get_reader()
    
    # Preprocess all images
    processed_images = [preprocess_image(img) for img in images]
    
    # Batch inference (EasyOCR handles this internally)
    results = []
    for img in processed_images:
        results.append(reader.readtext(img))
    
    return results
```

### 3. Optimal Settings with GPU

```python
GPU_OPTIMIZED_SETTINGS = {
    "upscale_scale": 5.0,  # Can handle higher upscaling
    "try_rotations": [0, 90, 180, 270, 15, -15, 30, -30],  # More angles
    "roi_top_k": 3,  # Check more regions
    "parallel_preprocessing": True,
    "batch_size": 4,  # Process multiple images together
}
```

## Benchmarking

### Speed Comparison Script

```python
# scripts/gpu_benchmark.py
import time
import torch
from app.pipeline.ocr_adapter import extract_serials

def benchmark_gpu_vs_cpu(image_path: str, iterations: int = 10):
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # CPU benchmark
    torch.cuda.is_available = lambda: False  # Force CPU
    start = time.time()
    for _ in range(iterations):
        _ = extract_serials(image_data)
    cpu_time = (time.time() - start) / iterations
    
    # GPU benchmark (if available)
    if torch.cuda.is_available():
        torch.cuda.is_available = lambda: True  # Force GPU
        torch.cuda.empty_cache()
        start = time.time()
        for _ in range(iterations):
            _ = extract_serials(image_data)
        gpu_time = (time.time() - start) / iterations
        
        print(f"CPU: {cpu_time:.3f}s per image")
        print(f"GPU: {gpu_time:.3f}s per image")
        print(f"Speedup: {cpu_time/gpu_time:.1f}x")
    else:
        print(f"CPU: {cpu_time:.3f}s per image")
        print("GPU not available")
```

## Cloud Deployment Options

### AWS EC2 with GPU
- Instance types: `g4dn.xlarge` (budget), `p3.2xlarge` (performance)
- AMI: Deep Learning AMI with PyTorch pre-installed
- Cost: $0.50-3.00/hour

### Google Cloud Platform
- Instance types: `n1-standard-4` with Tesla T4
- Image: Deep Learning VM with PyTorch
- Cost: $0.35-2.50/hour

### Azure
- Instance types: `NC6` (budget), `NC12` (performance)
- Image: Data Science Virtual Machine
- Cost: $0.60-3.50/hour

## Troubleshooting

### Common Issues

1. **CUDA out of memory**
   ```python
   # Reduce batch size or image resolution
   # Add memory cleanup after each request
   torch.cuda.empty_cache()
   ```

2. **CUDA not available**
   ```bash
   # Check NVIDIA driver
   nvidia-smi
   
   # Reinstall PyTorch with correct CUDA version
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Slow first inference**
   - Normal behavior - model loads to GPU on first use
   - Implement model preloading on startup

4. **Docker GPU not working**
   ```bash
   # Install nvidia-docker2
   distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
   curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
   curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
     sudo tee /etc/apt/sources.list.d/nvidia-docker.list
   sudo apt-get update && sudo apt-get install -y nvidia-docker2
   sudo systemctl restart docker
   ```

## Monitoring

### GPU Utilization
```bash
# Real-time monitoring
watch -n 1 nvidia-smi

# Python monitoring
import GPUtil
gpus = GPUtil.getGPUs()
for gpu in gpus:
    print(f"GPU {gpu.id}: {gpu.name}")
    print(f"  Memory: {gpu.memoryUsed}/{gpu.memoryTotal} MB")
    print(f"  Utilization: {gpu.load*100}%")
    print(f"  Temperature: {gpu.temperature}°C")
```

## Cost-Benefit Analysis

### When to Use GPU
✅ Production deployment with >100 requests/day
✅ Real-time processing requirements (<200ms)
✅ Batch processing of large datasets
✅ When accuracy requires heavy preprocessing

### When CPU is Sufficient
✅ Development and testing
✅ Low volume (<50 requests/day)
✅ Budget constraints
✅ Simple preprocessing pipeline

## Next Steps

1. Test GPU setup with `python -c "import torch; print(torch.cuda.is_available())"`
2. Update `app/config.py` to enable GPU
3. Run benchmark script to measure improvement
4. Adjust preprocessing parameters for GPU capacity
5. Monitor GPU utilization in production

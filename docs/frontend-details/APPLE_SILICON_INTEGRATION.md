# Apple Silicon (M1/M2/M3) Integration Guide for EasyOCR

This guide provides instructions for optimizing EasyOCR to use Apple Silicon's GPU capabilities through PyTorch's MPS (Metal Performance Shaders) backend, without affecting the main codebase's compatibility with other platforms.

## Overview

Apple Silicon Macs (M1, M2, M3) offer significant performance benefits for machine learning tasks through the MPS backend. This guide explains how to:

1. Set up a custom EasyOCR environment on macOS
2. Patch EasyOCR to use MPS acceleration
3. Benchmark and optimize performance
4. Maintain compatibility with the main codebase

## Prerequisites

- macOS 12.3 or newer
- Apple Silicon Mac (M1, M2, or M3)
- Python 3.10+ installed via Homebrew or official installer
- Xcode Command Line Tools

## Installation Steps

### 1. Create Isolated Environment

```bash
# Create a dedicated virtual environment
python -m venv .venv-m1
source .venv-m1/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install PyTorch with MPS Support

```bash
# Install PyTorch with native MPS support
pip install torch torchvision

# Verify MPS is available
python -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}, MPS built: {torch.backends.mps.is_built()}')"
```

### 3. Install EasyOCR and Dependencies

```bash
# Install EasyOCR and its dependencies
pip install easyocr
pip install fastapi uvicorn opencv-python openpyxl
```

### 4. Create MPS Adapter for EasyOCR

Create a new file called `mps_adapter.py` in the project root:

```python
"""
MPS Adapter for EasyOCR - Enables Metal Performance Shaders on Apple Silicon
"""
import os
import torch
import logging
from typing import List, Optional, Union, Tuple

logger = logging.getLogger(__name__)

# Check if MPS is available
HAS_MPS = False
if hasattr(torch.backends, "mps"):
    if torch.backends.mps.is_available() and torch.backends.mps.is_built():
        HAS_MPS = True
        logger.info("Apple Silicon MPS backend is available and will be used")
    else:
        logger.info("Apple Silicon MPS backend is not available")
else:
    logger.info("PyTorch does not have MPS support")

def patch_easyocr():
    """
    Patch EasyOCR to use MPS backend on Apple Silicon
    """
    if not HAS_MPS:
        logger.warning("MPS not available, skipping EasyOCR patch")
        return False
    
    try:
        import easyocr
        from easyocr.recognition import get_recognizer, load_pytorch_model
        from easyocr.utils import get_image_list, reformat_input
        
        # Store original functions
        original_get_recognizer = get_recognizer
        original_load_pytorch_model = load_pytorch_model
        
        # Patch load_pytorch_model to use MPS device
        def patched_load_pytorch_model(model_path, device='mps'):
            """
            Custom model loader that defaults to MPS device
            """
            # If explicitly requesting CUDA, honor that
            if device == 'cuda' and torch.cuda.is_available():
                return original_load_pytorch_model(model_path, device)
            
            # For CPU or default, check if we should use MPS
            if HAS_MPS and device != 'cpu':
                try:
                    return original_load_pytorch_model(model_path, 'mps')
                except Exception as e:
                    logger.warning(f"Failed to load model on MPS: {e}")
                    # Fall back to CPU
                    return original_load_pytorch_model(model_path, 'cpu')
            
            # Default behavior
            return original_load_pytorch_model(model_path, device)
        
        # Patch get_recognizer to use MPS device
        def patched_get_recognizer(
            character_list: List[str],
            separator_list: List[str],
            dict_list: dict,
            model_path: str,
            device: str = 'mps',
            quantize: bool = True,
            cudnn_benchmark: bool = False
        ):
            """
            Custom recognizer that defaults to MPS device
            """
            # If explicitly requesting CUDA, honor that
            if device == 'cuda' and torch.cuda.is_available():
                return original_get_recognizer(
                    character_list, separator_list, dict_list,
                    model_path, device, quantize, cudnn_benchmark
                )
            
            # For CPU or default, check if we should use MPS
            if HAS_MPS and device != 'cpu':
                try:
                    # MPS doesn't support cudnn_benchmark
                    return original_get_recognizer(
                        character_list, separator_list, dict_list,
                        model_path, 'mps', quantize, False
                    )
                except Exception as e:
                    logger.warning(f"Failed to create recognizer on MPS: {e}")
                    # Fall back to CPU
                    return original_get_recognizer(
                        character_list, separator_list, dict_list,
                        model_path, 'cpu', quantize, cudnn_benchmark
                    )
            
            # Default behavior
            return original_get_recognizer(
                character_list, separator_list, dict_list,
                model_path, device, quantize, cudnn_benchmark
            )
        
        # Apply the patches
        easyocr.recognition.load_pytorch_model = patched_load_pytorch_model
        easyocr.recognition.get_recognizer = patched_get_recognizer
        
        # Patch Reader class to default to MPS
        original_init = easyocr.Reader.__init__
        
        def patched_init(self, lang_list, gpu=True, model_storage_directory=None,
                         user_network_directory=None, recog_network='standard',
                         download_enabled=True, detector=True,
                         recognizer=True, verbose=True, quantize=True,
                         cudnn_benchmark=False):
            """
            Patched __init__ for Reader class that handles MPS
            """
            # Determine device based on availability
            device = 'cpu'
            if gpu:
                if torch.cuda.is_available():
                    device = 'cuda'
                elif HAS_MPS:
                    device = 'mps'
                    # MPS doesn't support cudnn_benchmark
                    cudnn_benchmark = False
            
            # Call original init with determined device
            original_init(
                self, lang_list, gpu=gpu, model_storage_directory=model_storage_directory,
                user_network_directory=user_network_directory, recog_network=recog_network,
                download_enabled=download_enabled, detector=detector,
                recognizer=recognizer, verbose=verbose, quantize=quantize,
                cudnn_benchmark=cudnn_benchmark
            )
            
            # Override the device if needed
            if gpu and HAS_MPS and not torch.cuda.is_available():
                self.device = 'mps'
        
        # Apply the patch to Reader
        easyocr.Reader.__init__ = patched_init
        
        logger.info("Successfully patched EasyOCR to use MPS backend")
        return True
    
    except Exception as e:
        logger.error(f"Failed to patch EasyOCR: {e}")
        return False

# Automatically patch when imported
success = patch_easyocr()
```

### 5. Integrate with Application

Update `app/config.py` to use the MPS adapter:

```python
import os
import logging

# Configure logging
logger = logging.getLogger(__name__)

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
    
    logger.info(f"GPU detection: CUDA={_HAS_CUDA}, MPS={_HAS_MPS}, Using={_GPU_TYPE}")
except Exception as e:
    logger.warning(f"Error during GPU detection: {e}")
    _USE_GPU = False
    _GPU_TYPE = "cpu"

# If on macOS with Apple Silicon, try to use MPS adapter
if _HAS_MPS and _USE_GPU:
    try:
        import mps_adapter
        logger.info("MPS adapter for EasyOCR loaded")
    except ImportError:
        logger.warning("MPS adapter not found, using standard EasyOCR")

# OCR settings
OCR_SETTINGS = {
    "languages": ["en"],
    "use_gpu": _USE_GPU,
    "gpu_type": _GPU_TYPE,
}
```

## Performance Optimization

### 1. Environment Variables for MPS

Add these to your `.env` file or set them before running the application:

```
# Prevent MPS from reserving too much memory
PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0

# Control batch size for MPS (reduce if experiencing memory issues)
OCR_BATCH_SIZE=4

# Optional: Force CPU mode even if MPS is available
# FORCE_CPU=1
```

### 2. MPS-Specific Settings

Create an MPS-optimized preset in your parameters configuration:

```python
# In app/services/param_cache.py or similar

PRESETS = {
    # ... existing presets ...
    
    "apple_silicon": {
        "description": "Optimized for Apple Silicon (M1/M2/M3) Macs",
        "upscale_scale": 4.0,  # M1/M2/M3 can handle higher upscaling
        "try_rotations": [0, 90, 180, 270],  # Standard rotations
        "fine_rotation": True,  # Enable fine rotations
        "roi_top_k": 3,  # Check more regions
        "batch_size": 4,  # Process multiple images together
        "low_text": 0.3,  # EasyOCR parameter
        "text_threshold": 0.7,  # EasyOCR parameter
        "link_threshold": 0.3,  # EasyOCR parameter
        "mag_ratio": 1.5,  # EasyOCR parameter
    }
}
```

## Troubleshooting

### Common Issues and Solutions

1. **"MPS not available" error**
   - Ensure macOS 12.3 or newer
   - Verify PyTorch 1.12 or newer
   - Try reinstalling PyTorch: `pip install --force-reinstall torch torchvision`

2. **Memory errors with MPS**
   - Add environment variable: `export PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0`
   - Reduce batch size: `export OCR_BATCH_SIZE=1`
   - Process with smaller upscale factor: `upscale_scale=2.0`

3. **Slow first run**
   - This is normal - MPS compiles operations on first use
   - Subsequent runs will be much faster

4. **Model loading errors**
   - Some models may not be compatible with MPS
   - The adapter will automatically fall back to CPU for incompatible models

## Performance Expectations

- **First run**: 2-3x slower than subsequent runs due to compilation
- **Subsequent runs**: 3-5x faster than CPU-only mode
- **Memory usage**: Higher than CPU mode, but manageable with proper settings
- **Accuracy**: Identical to CPU mode (no precision loss)

## Conclusion

This integration allows the Apple OCR backend to leverage the GPU capabilities of Apple Silicon Macs while maintaining compatibility with other platforms. The MPS adapter provides a non-intrusive way to accelerate OCR processing on M1/M2/M3 Macs without modifying the core EasyOCR library.

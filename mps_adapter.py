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
        from easyocr.recognition import get_recognizer
        from easyocr.utils import get_image_list, reformat_input
        
        # Store original functions
        original_get_recognizer = get_recognizer
        
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

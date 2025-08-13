"""
Parameter cache service for storing and retrieving best OCR parameters.

This module provides functionality to:
1. Cache best parameters per device preset
2. Load cached parameters
3. Schedule and run automated parameter sweeps
"""

import os
import json
import time
import threading
from typing import Dict, Any, Optional
from pathlib import Path

# Cache file locations
CACHE_DIR = Path("data/param_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Lock for thread safety when updating cache
_cache_lock = threading.Lock()


def get_cache_path(preset: str) -> Path:
    """Get the path to the cache file for a specific preset."""
    return CACHE_DIR / f"{preset}_best_params.json"


def save_best_params(preset: str, params: Dict[str, Any], accuracy: float) -> None:
    """
    Save best parameters for a device preset to the cache.
    
    Args:
        preset: Device preset name (e.g., 'etched', 'sticker')
        params: Dictionary of best parameters
        accuracy: Accuracy achieved with these parameters
    """
    cache_path = get_cache_path(preset)
    
    # Add metadata
    cache_data = {
        "preset": preset,
        "params": params,
        "accuracy": accuracy,
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    with _cache_lock:
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f, indent=2)


def load_best_params(preset: str) -> Optional[Dict[str, Any]]:
    """
    Load best parameters for a device preset from the cache.
    
    Args:
        preset: Device preset name (e.g., 'etched', 'sticker')
        
    Returns:
        Dictionary with parameters and metadata, or None if not found
    """
    cache_path = get_cache_path(preset)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def get_best_params(preset: str) -> Optional[Dict[str, Any]]:
    """
    Get only the parameter values (not metadata) for a preset.
    
    Args:
        preset: Device preset name
        
    Returns:
        Dictionary with just the parameters, or None if not found
    """
    cache_data = load_best_params(preset)
    if cache_data and "params" in cache_data:
        return cache_data["params"]
    return None


def list_cached_presets() -> Dict[str, Dict[str, Any]]:
    """
    List all presets that have cached parameters.
    
    Returns:
        Dictionary mapping preset names to their metadata
    """
    result = {}
    
    for cache_file in CACHE_DIR.glob("*_best_params.json"):
        preset = cache_file.stem.replace("_best_params", "")
        cache_data = load_best_params(preset)
        if cache_data:
            result[preset] = {
                "accuracy": cache_data.get("accuracy"),
                "date": cache_data.get("date"),
                "timestamp": cache_data.get("timestamp")
            }
    
    return result


# Background sweep scheduler
_sweep_thread = None
_sweep_running = False


def _run_param_sweep(preset: str, images_dir: str, labels_file: str) -> None:
    """
    Run a parameter sweep in the background.
    
    Args:
        preset: Device preset to optimize
        images_dir: Directory with test images
        labels_file: Path to labels CSV file
    """
    global _sweep_running
    
    try:
        _sweep_running = True
        
        # Import here to avoid circular imports
        import subprocess
        import sys
        
        # Build the command
        cmd = [
            sys.executable, "scripts/param_sweep.py",
            "--images", images_dir,
            "--labels", labels_file,
            "--output", f"exports/param_sweep_{preset}.csv",
            "--quick"  # Use quick mode for automated sweeps
        ]
        
        # Run the sweep
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            # Sweep completed successfully, load the results
            best_params_file = f"exports/param_sweep_{preset}_best.json"
            if os.path.exists(best_params_file):
                with open(best_params_file, 'r') as f:
                    best_data = json.load(f)
                    
                # Save to our cache
                save_best_params(
                    preset, 
                    best_data.get("params", {}), 
                    best_data.get("accuracy", 0.0)
                )
        else:
            print(f"Parameter sweep failed: {result.stderr}")
    
    finally:
        _sweep_running = False


def schedule_param_sweep(preset: str, images_dir: str, labels_file: str) -> bool:
    """
    Schedule a parameter sweep to run in the background.
    
    Args:
        preset: Device preset to optimize
        images_dir: Directory with test images
        labels_file: Path to labels CSV file
        
    Returns:
        True if sweep was scheduled, False if already running
    """
    global _sweep_thread, _sweep_running
    
    if _sweep_running:
        return False
    
    _sweep_thread = threading.Thread(
        target=_run_param_sweep,
        args=(preset, images_dir, labels_file),
        daemon=True
    )
    _sweep_thread.start()
    return True


def is_sweep_running() -> bool:
    """Check if a parameter sweep is currently running."""
    return _sweep_running

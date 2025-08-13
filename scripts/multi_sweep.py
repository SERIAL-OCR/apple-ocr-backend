#!/usr/bin/env python3
"""
Multi-run parameter sweep automation.

This script runs parameter sweeps for multiple device presets and
stores the best parameters in the cache.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Add the parent directory to the path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.param_cache import save_best_params, list_cached_presets


def run_sweep_for_preset(
    preset: str,
    images_dir: str,
    labels_file: str,
    timeout: int = 60,
    quick: bool = False,
) -> Dict[str, Any]:
    """Run parameter sweep for a specific preset."""
    import subprocess
    
    output_file = f"exports/param_sweep_{preset}.csv"
    best_params_file = output_file.replace('.csv', '_best.json')
    
    # Build command
    cmd = [
        sys.executable, "scripts/param_sweep.py",
        "--images", images_dir,
        "--labels", labels_file,
        "--output", output_file,
        "--timeout", str(timeout),
    ]
    
    if quick:
        cmd.append("--quick")
    
    # Run the sweep
    print(f"\n{'='*60}")
    print(f"Running parameter sweep for preset: {preset}")
    print(f"{'='*60}")
    
    process = subprocess.run(cmd)
    
    if process.returncode != 0:
        print(f"Error running sweep for preset {preset}")
        return {}
    
    # Load the best parameters
    if not os.path.exists(best_params_file):
        print(f"No best parameters file found for {preset}")
        return {}
    
    with open(best_params_file, 'r') as f:
        best_data = json.load(f)
    
    # Save to cache
    params = best_data.get("params", {})
    accuracy = best_data.get("accuracy", 0.0)
    
    save_best_params(preset, params, accuracy)
    
    return best_data


def run_all_sweeps(
    presets: List[str],
    images_dir: str,
    labels_file: str,
    timeout: int = 60,
    quick: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Run parameter sweeps for all specified presets."""
    results = {}
    
    for preset in presets:
        start_time = time.time()
        best_data = run_sweep_for_preset(
            preset, images_dir, labels_file, timeout, quick
        )
        elapsed = time.time() - start_time
        
        results[preset] = {
            "accuracy": best_data.get("accuracy", 0.0),
            "params": best_data.get("params", {}),
            "elapsed_seconds": elapsed,
        }
        
        print(f"Completed sweep for {preset} in {elapsed:.1f} seconds")
        print(f"Accuracy: {best_data.get('accuracy', 0.0):.2%}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Run parameter sweeps for multiple presets")
    parser.add_argument("--presets", nargs="+", default=["etched", "sticker", "screen", "default"],
                       help="Device presets to optimize")
    parser.add_argument("--images", default="exported-assets",
                       help="Directory containing test images")
    parser.add_argument("--labels", default="exported-assets/labels.csv",
                       help="CSV file with ground truth")
    parser.add_argument("--timeout", type=int, default=60,
                       help="HTTP timeout seconds per image")
    parser.add_argument("--quick", action="store_true",
                       help="Use quick mode with fewer parameter combinations")
    parser.add_argument("--list-cache", action="store_true",
                       help="List cached parameters instead of running sweeps")
    
    args = parser.parse_args()
    
    # List cached parameters if requested
    if args.list_cache:
        cached = list_cached_presets()
        if not cached:
            print("No cached parameters found")
            return
        
        print("\nCached parameters:")
        for preset, metadata in cached.items():
            print(f"  {preset}: {metadata['accuracy']:.2%} accuracy (updated: {metadata['date']})")
        return
    
    # Ensure output directory exists
    os.makedirs("exports", exist_ok=True)
    
    # Run sweeps
    print(f"Running parameter sweeps for presets: {', '.join(args.presets)}")
    print(f"Using images from: {args.images}")
    print(f"Using labels from: {args.labels}")
    
    results = run_all_sweeps(
        args.presets,
        args.images,
        args.labels,
        args.timeout,
        args.quick,
    )
    
    # Print summary
    print("\nSweep results summary:")
    for preset, data in results.items():
        print(f"  {preset}: {data['accuracy']:.2%} accuracy")
    
    # Save overall summary
    summary_file = "exports/multi_sweep_summary.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nSummary saved to {summary_file}")


if __name__ == "__main__":
    main()

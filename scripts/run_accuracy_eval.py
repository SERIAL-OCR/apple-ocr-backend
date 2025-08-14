"""
Run comprehensive accuracy evaluation on different datasets with various presets.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.config import DEVICE_PRESETS
from app.services.eval import evaluate_dataset


def run_evaluation(
    dataset_dir: str,
    preset: Optional[str] = None,
    use_progressive: bool = True,
    save_debug_images: bool = False,
    min_confidence: float = 0.0,
) -> Dict:
    """Run evaluation on a dataset with specified preset."""
    print(f"\n{'=' * 80}")
    print(f"Evaluating dataset: {dataset_dir}")
    print(f"Preset: {preset or 'default'}")
    print(f"Progressive processing: {'enabled' if use_progressive else 'disabled'}")
    print(f"{'=' * 80}\n")
    
    extract_params = {}
    if preset and preset in DEVICE_PRESETS:
        extract_params = DEVICE_PRESETS[preset].copy()
        print(f"Using preset parameters: {preset}")
    elif preset:
        print(f"Warning: Unknown preset '{preset}', using default parameters")
    
    result = evaluate_dataset(
        dataset_dir=dataset_dir,
        min_confidence=min_confidence,
        extract_params=extract_params,
        use_progressive=use_progressive,
        save_debug_images=save_debug_images,
    )
    
    # Print summary
    print("\nEvaluation Results:")
    print(f"  Total images: {result['total']}")
    print(f"  Serials detected: {result['detected']} ({result['detection_rate_pct']}%)")
    print(f"  Correct matches: {result['hits']} ({result['accuracy_pct_overall']}%)")
    print(f"  Accuracy on detected: {result['accuracy_pct_on_detected']}%")
    print(f"  Strict validation passes: {result['strict_validation_passes']} ({result['strict_validation_rate_pct']}%)")
    print(f"  High confidence accuracy: {result['high_confidence_accuracy_pct']}% ({result['high_confidence_hits']}/{result['high_confidence_count']})")
    print(f"\nDetailed results saved to: {result['csv_path']}")
    print(f"Summary saved to: {result['summary_path']}")
    
    return result


def run_multi_preset_evaluation(
    dataset_dir: str,
    presets: List[str],
    use_progressive: bool = True,
    save_debug_images: bool = False,
) -> None:
    """Run evaluation with multiple presets and compare results."""
    results = {}
    
    for preset in presets:
        results[preset] = run_evaluation(
            dataset_dir=dataset_dir,
            preset=preset,
            use_progressive=use_progressive,
            save_debug_images=save_debug_images,
        )
    
    # Save comparative results
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    reports_dir = os.path.join("exports", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    compare_path = os.path.join(
        reports_dir, 
        f"compare_{os.path.basename(os.path.normpath(dataset_dir))}_{ts}.json"
    )
    
    with open(compare_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    # Print comparison
    print("\n\nPreset Comparison:")
    print(f"{'Preset':<15} {'Detection':<10} {'Accuracy':<10} {'High Conf':<10}")
    print("-" * 50)
    
    for preset, result in results.items():
        print(
            f"{preset:<15} "
            f"{result['detection_rate_pct']:<10.1f} "
            f"{result['accuracy_pct_overall']:<10.1f} "
            f"{result['high_confidence_accuracy_pct']:<10.1f}"
        )
    
    # Find best preset
    best_preset = max(results.items(), key=lambda x: x[1]["accuracy_pct_overall"])
    print(f"\nBest preset by overall accuracy: {best_preset[0]} ({best_preset[1]['accuracy_pct_overall']}%)")
    
    best_high_conf = max(results.items(), key=lambda x: x[1]["high_confidence_accuracy_pct"])
    print(f"Best preset by high confidence accuracy: {best_high_conf[0]} ({best_high_conf[1]['high_confidence_accuracy_pct']}%)")
    
    print(f"\nComparison saved to: {compare_path}")


def main():
    parser = argparse.ArgumentParser(description="Run OCR accuracy evaluation")
    parser.add_argument(
        "dataset_dir", 
        help="Directory containing images to evaluate (should have labels.csv)"
    )
    parser.add_argument(
        "--preset", 
        help="Device preset to use (etched, sticker, screen, etc.)"
    )
    parser.add_argument(
        "--all-presets", 
        action="store_true",
        help="Run evaluation with all available presets"
    )
    parser.add_argument(
        "--no-progressive", 
        action="store_true",
        help="Disable progressive processing"
    )
    parser.add_argument(
        "--save-debug", 
        action="store_true",
        help="Save debug images"
    )
    parser.add_argument(
        "--min-confidence", 
        type=float,
        default=0.0,
        help="Minimum confidence threshold"
    )
    
    args = parser.parse_args()
    
    if args.all_presets:
        # Run with all presets
        presets = list(DEVICE_PRESETS.keys())
        run_multi_preset_evaluation(
            dataset_dir=args.dataset_dir,
            presets=presets,
            use_progressive=not args.no_progressive,
            save_debug_images=args.save_debug,
        )
    else:
        # Run with single preset
        run_evaluation(
            dataset_dir=args.dataset_dir,
            preset=args.preset,
            use_progressive=not args.no_progressive,
            save_debug_images=args.save_debug,
            min_confidence=args.min_confidence,
        )


if __name__ == "__main__":
    main()

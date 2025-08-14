# Run accuracy evaluation on the Apple serial dataset with all presets
python scripts/run_accuracy_eval.py "Apple serial" --all-presets --save-debug

# Run progressive processing evaluation on the Apple serial dataset
python scripts/run_accuracy_eval.py "Apple serial" --save-debug

# Run evaluation with the best preset based on previous results
python scripts/run_accuracy_eval.py "Apple serial" --preset etched-dark --save-debug

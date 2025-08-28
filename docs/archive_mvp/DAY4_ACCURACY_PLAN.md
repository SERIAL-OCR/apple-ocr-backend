# Day 4 Plan: Accuracy Optimization for Real-World Apple Serial OCR

## Current Accuracy Analysis

Based on our testing and logs, we've achieved:
- **Synthetic images**: ~44% accuracy with best parameters
- **Real-world images**: ~60% accuracy on the "Apple serial" folder
- **Best performing configuration**: 
  - Preset: default/etched
  - Mode: grayscale
  - Upscale: 4.0-5.0x
  - ROI detection with adaptive padding
  - Glare reduction: adaptive/division
  - Fine rotations enabled

## Key Challenges Identified

1. **Timeout issues**: Processing is too slow with current settings (90s+ timeouts)
2. **Character confusion**: Particularly G/6, A/4, O/0, B/8
3. **Glare/reflection**: Especially on etched metal surfaces
4. **Small text**: Hard to detect without significant upscaling
5. **Variable backgrounds**: Different materials (metal, screen, sticker)
6. **GPU memory limitations**: OOM errors with heavy settings

## Day 4 Optimization Plan

### 1. Performance Optimization (Morning)

- **Reduce processing time**:
  - Implement early stopping when high-confidence match is found
  - Add progressive processing (start with fast settings, only use slow settings if needed)
  - Optimize ROI detection to reduce false positives
  - Add caching for intermediate processing results

- **GPU memory management**:
  - Implement batch size control for EasyOCR
  - Add automatic downscaling for very large images
  - Implement memory monitoring to avoid OOM errors

### 2. Character Recognition Enhancement (Late Morning)

- **Improve character disambiguation**:
  - Train a specialized classifier for ambiguous character pairs (G/6, B/8)
  - Implement context-aware correction using Apple serial patterns
  - Add post-processing rules based on character position

- **Serial number validation**:
  - Expand known Apple serial prefixes database
  - Implement position-specific character rules
  - Add checksum validation if applicable

### 3. Image Preprocessing Refinement (Afternoon)

- **Advanced glare handling**:
  - Implement multi-scale glare detection
  - Add local contrast enhancement for etched serials
  - Implement shadow removal techniques

- **Zoom and focus improvements**:
  - Refine keyword-guided cropping with better text localization
  - Implement smart zoom that focuses on text density regions
  - Add edge enhancement specifically for etched text

### 4. Test-Time Augmentation Optimization (Late Afternoon)

- **Smarter rotation strategy**:
  - Implement orientation detection to reduce unnecessary rotations
  - Use image features to prioritize likely orientations
  - Add skew correction for perspective distortion

- **Multiple preprocessing paths**:
  - Run parallel preprocessing pipelines and select best results
  - Implement voting mechanism across different processing methods
  - Add confidence calibration based on image characteristics

### 5. Evaluation and Fine-Tuning (End of Day)

- **Comprehensive evaluation**:
  - Run full evaluation on all real images with new optimizations
  - Generate detailed error analysis by image type
  - Identify remaining failure cases and patterns

- **Parameter optimization**:
  - Run targeted parameter sweeps for specific image types
  - Create additional specialized presets (e.g., "etched-dark", "etched-light")
  - Fine-tune character recognition thresholds

## Implementation Priorities

1. **High impact, low effort**:
   - Early stopping mechanism
   - Enhanced character disambiguation
   - Expanded validation rules
   - Local contrast enhancement

2. **High impact, medium effort**:
   - Progressive processing pipeline
   - Smart rotation strategy
   - Multi-scale glare detection
   - Specialized character classifier

3. **If time permits**:
   - Parallel preprocessing paths
   - Advanced perspective correction
   - Memory optimization for GPU
   - Confidence calibration

## Success Metrics

- **Primary goal**: Increase real-world accuracy from ~60% to 80%+
- **Secondary goals**:
  - Reduce average processing time by 50%
  - Eliminate timeout errors
  - Achieve 90%+ accuracy on etched serials specifically
  - Improve confidence scores on correct detections

## Technical Implementation Details

### Early Stopping Mechanism

```python
def extract_serials(image_bytes, min_confidence=0.0, early_stop_confidence=0.95, ...):
    # Process with standard rotations first
    for angle in [0, 180]:  # Try most common orientations first
        results = _read_serials_from_image(...)
        
        # Early stopping if high-confidence match found
        for serial, confidence in results:
            if is_valid_apple_serial(serial) and confidence > early_stop_confidence:
                return [(serial, confidence)]
                
    # Continue with more expensive processing only if needed
    # ...
```

### Progressive Processing Pipeline

```python
def progressive_process(image_bytes, min_confidence=0.0):
    # Stage 1: Fast processing (grayscale, basic preprocessing, no rotations)
    results = extract_serials(
        image_bytes, 
        min_confidence=min_confidence,
        try_rotations=[0, 180],
        roi=True,
        fine_rotation=False,
        upscale_scale=2.0
    )
    
    if results and results[0][1] > 0.8:
        return results
        
    # Stage 2: Medium processing (add more rotations, better preprocessing)
    results = extract_serials(
        image_bytes,
        min_confidence=min_confidence,
        try_rotations=[0, 90, 180, 270],
        roi=True,
        fine_rotation=False,
        upscale_scale=3.0,
        glare_reduction="adaptive"
    )
    
    if results and results[0][1] > 0.7:
        return results
        
    # Stage 3: Full processing (all optimizations)
    return extract_serials(
        image_bytes,
        min_confidence=min_confidence,
        try_rotations=[0, 90, 180, 270],
        roi=True,
        fine_rotation=True,
        upscale_scale=4.0,
        glare_reduction="adaptive",
        keyword_crop=True
    )
```

### Enhanced Character Disambiguation

```python
def _enhanced_normalize_ambiguous(text, position_aware=True):
    """Position-aware character disambiguation."""
    result = ""
    for i, char in enumerate(text):
        if position_aware:
            # Apply position-specific rules
            if char == 'G' and i >= 8:  # Last 4 chars more likely to be digits
                result += '6'
            elif char == 'O' and i < 3:  # First 3 chars more likely to be letters
                result += 'O'
            # ... more position rules
            else:
                result += _AMBIGUOUS_MAP.get(char, char)
        else:
            result += _AMBIGUOUS_MAP.get(char, char)
    return result
```

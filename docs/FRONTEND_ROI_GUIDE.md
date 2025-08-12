# Frontend ROI Cropping Guide

## Overview
To maximize OCR accuracy, the iOS frontend should implement intelligent Region of Interest (ROI) cropping before sending images to the backend. This reduces noise, glare, and processing time while improving detection rates.

## Requirements

### 1. User Interface Guidelines

#### Capture Overlay
- Display a rectangular guide overlay on the camera preview
- Guide dimensions: ~70% of screen width, ~20% of screen height
- Center the guide horizontally, position at 40% from top
- Semi-transparent border with corner markers
- Text prompt: "Align serial number within frame"

#### Visual Feedback
- Real-time edge detection highlighting (optional)
- Green border when text is detected in frame
- Red border when image is too blurry or dark
- Haptic feedback on successful capture

### 2. Image Preprocessing (iOS Side)

#### Automatic Cropping
```swift
// Recommended crop padding
let padding = CGFloat(50) // pixels
let cropRect = CGRect(
    x: max(0, detectedTextRegion.minX - padding),
    y: max(0, detectedTextRegion.minY - padding),
    width: min(image.width, detectedTextRegion.width + padding * 2),
    height: min(image.height, detectedTextRegion.height + padding * 2)
)
```

#### Quality Checks Before Upload
1. **Blur Detection**: Laplacian variance > 100
2. **Brightness Check**: Mean pixel value between 50-200
3. **Minimum Resolution**: Cropped region >= 300x100 pixels
4. **Aspect Ratio**: Between 2:1 and 10:1 (typical for serial numbers)

### 3. VisionKit Integration

Use iOS VisionKit for initial text detection:

```swift
import Vision

func detectTextRegion(in image: UIImage, completion: @escaping (CGRect?) -> Void) {
    guard let cgImage = image.cgImage else { 
        completion(nil)
        return 
    }
    
    let request = VNDetectTextRectanglesRequest { request, error in
        guard let observations = request.results as? [VNTextObservation],
              let textBox = observations.first?.boundingBox else {
            completion(nil)
            return
        }
        
        // Convert Vision coordinates to UIKit coordinates
        let imageSize = CGSize(width: cgImage.width, height: cgImage.height)
        let rect = VNImageRectForNormalizedRect(textBox, 
                                                Int(imageSize.width), 
                                                Int(imageSize.height))
        completion(rect)
    }
    
    request.reportCharacterBoxes = false
    let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
    try? handler.perform([request])
}
```

### 4. API Integration

#### Request Format
```json
{
  "image": "base64_encoded_cropped_image",
  "metadata": {
    "original_dimensions": [2048, 1536],
    "crop_region": [512, 384, 1024, 256],
    "device_model": "iPhone14,2",
    "capture_mode": "auto",
    "preprocessing": {
      "blur_score": 156.2,
      "brightness": 128,
      "has_flash": false
    }
  }
}
```

#### Recommended Headers
```
X-Device-Type: iPhone
X-Image-Preprocessed: true
X-ROI-Applied: true
```

### 5. Device-Specific Optimizations

#### For Etched Serials (MacBooks, Metal Devices)
- Increase exposure slightly (+0.5 EV)
- Disable flash (causes glare on metal)
- Use `preset=etched` in API call

#### For Sticker Labels
- Enable auto-flash in low light
- Normal exposure
- Use `preset=sticker` in API call

#### For Screen Display
- Reduce exposure (-0.5 EV) to prevent overexposure
- Disable flash
- Use `preset=screen` in API call

### 6. Error Handling

#### Retry Logic
1. If no text detected: Prompt user to adjust angle/lighting
2. If blur detected: Show "Hold steady" message
3. If too dark: Suggest better lighting or enable torch
4. After 3 failed attempts: Offer manual full-frame capture

#### Fallback Mode
If ROI detection fails consistently:
- Send full image with `roi=false` parameter
- Let backend handle the complete processing
- Log failure for debugging

### 7. Performance Considerations

#### Image Compression
- Use JPEG with 85% quality for cropped regions
- Maximum upload size: 2MB
- Resize if needed while maintaining aspect ratio

#### Caching
- Cache successful detection parameters per device type
- Reuse optimal settings for subsequent captures

### 8. Testing Checklist

- [ ] Test with various lighting conditions
- [ ] Test with different angles (0°, 15°, 30°, 45°)
- [ ] Test with worn/faded serials
- [ ] Test with reflective surfaces
- [ ] Test with different font sizes
- [ ] Verify crop padding is sufficient
- [ ] Ensure metadata is correctly attached
- [ ] Validate retry mechanism works

## Sample Implementation Flow

```
1. User opens camera
2. Display ROI guide overlay
3. Run continuous text detection (throttled to 2 FPS)
4. When text detected in guide area:
   a. Check image quality
   b. Crop with padding
   c. Apply device-specific preprocessing
   d. Upload to backend with metadata
5. Display result or retry prompt
```

## Backend Coordination

The backend will:
- Accept pre-cropped images with metadata
- Apply additional preprocessing based on device type
- Return confidence scores and detected serials
- Log failed detections for improvement

## Benefits of Frontend ROI

1. **Reduced Bandwidth**: ~70% smaller uploads
2. **Faster Processing**: 2-3x faster OCR
3. **Better Accuracy**: 15-20% improvement
4. **Lower Server Load**: Less preprocessing needed
5. **Better UX**: Immediate feedback to user

# Frontend ROI Crop Integration Guide

This guide outlines how to integrate the backend's Region of Interest (ROI) cropping capabilities with the iOS frontend.

## Overview

Our OCR backend includes sophisticated ROI detection to isolate text regions, but providing a pre-cropped image from the frontend can further improve accuracy and reduce processing time.

## Implementation Steps

### 1. Manual ROI Selection

- Add a rectangular selection overlay on the camera preview
- Allow users to adjust the rectangle to frame the serial number
- Crop the image to the selected ROI before sending
- Maintain a reasonable margin around the text (approximately 10-20% padding)

### 2. Device Type Selection

- Add a UI for users to select the device type (MacBook, iPhone, iPad, etc.)
- Map device types to appropriate presets:
  - `etched`: For MacBook, Mac Mini, iMac (metal etched serials)
  - `sticker`: For accessories, boxes (printed labels)
  - `screen`: For on-screen display of serials (Settings app)
  - `default`: General purpose preset

### 3. API Integration

When sending the image to the backend, include these parameters:

- `preset`: The processing preset to use (`etched`, `sticker`, `screen`, `default`)
- `device_type`: The type of device being scanned (for logging/analytics)

## Example Request

```
POST /process-serial
Content-Type: multipart/form-data

- image: [binary image data]
- preset: etched
- device_type: MacBook Pro
```

## Best Practices

1. **Provide clear user guidance**:
   - Show an example of a properly framed serial number
   - Use visual guides to help users position the ROI correctly

2. **Handle different orientations**:
   - Support both landscape and portrait orientations
   - Adjust the ROI aspect ratio based on typical serial number dimensions

3. **Error handling**:
   - Provide feedback if the selected area is too small
   - Allow users to retake/recrop if OCR fails

## Backend API Parameters

| Parameter | Description | Example Values |
|-----------|-------------|----------------|
| `preset` | Predefined settings for device type | `"etched"`, `"sticker"`, `"screen"`, `"default"` |
| `device_type` | Type of device being scanned | `"MacBook"`, `"iPhone"`, `"iPad"` |
| `min_confidence` | Minimum confidence threshold | `0.5` (range: 0.0-1.0) |
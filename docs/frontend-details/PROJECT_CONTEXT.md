# Apple OCR Project Context

## Project Overview

The Apple Serial OCR project consists of two main components:
1. A backend service (Python/FastAPI) for OCR processing
2. An iOS frontend app for capturing and processing images

This document provides context from our discussions and development planning.

## Project Background

The project aims to create a system for accurately recognizing and processing Apple device serial numbers from images. The system is designed as a 7-day MVP (Minimum Viable Product) with the following goals:

- Achieve 90%+ OCR accuracy for Apple serial numbers
- Create a smooth user experience for capturing serial numbers
- Provide robust validation of detected serial numbers
- Enable export capabilities for business reporting

## Current Status

The backend service has been developed with the following features:
- EasyOCR integration with custom preprocessing
- API endpoints for image processing
- Parameter optimization for different device types
- GPU acceleration support (CUDA and Apple Silicon MPS)
- Evaluation and benchmarking tools

The iOS frontend is in the planning stage with detailed documentation created for:
- Project structure and architecture
- Development timeline
- Technical implementation details
- Backend integration approach

## Key Technical Decisions

### Backend

1. **OCR Engine**: EasyOCR was selected as the primary OCR engine with Tesseract as a fallback
2. **Preprocessing Pipeline**: Custom preprocessing for Apple device surfaces (aluminum/glass)
3. **Device-specific Presets**: Different processing parameters for etched, sticker, and screen serials
4. **GPU Acceleration**: Support for both NVIDIA CUDA and Apple Silicon MPS
5. **Validation**: Apple-specific serial number pattern validation

### Frontend

1. **Native iOS**: SwiftUI-based iOS app for optimal camera integration
2. **ROI Selection**: Custom Region of Interest selection for better accuracy
3. **Device Type Selection**: User interface for selecting device type
4. **Offline Support**: Basic functionality when network is unavailable
5. **History Management**: Local storage of scan history

## Development Priorities

1. **Day 1-2**: Core OCR functionality in backend
2. **Day 3**: API endpoints and validation
3. **Day 4**: iOS frontend camera integration
4. **Day 5**: Frontend-backend integration
5. **Day 6**: Export and reporting features
6. **Day 7**: Final polish and demo preparation

## Technical Challenges

1. **Glare and Reflections**: Apple devices often have reflective surfaces
2. **Small Text**: Serial numbers can be very small, especially on accessories
3. **Variable Backgrounds**: Different materials (metal, screen, sticker)
4. **Performance**: Balancing accuracy vs. speed for mobile use
5. **GPU Memory**: Managing memory usage for GPU acceleration

## Implementation Insights

### OCR Optimization

- **Upscaling**: 2x-5x upscaling improves recognition of small text
- **Inverted Images**: Processing both normal and inverted images improves results
- **Character Allowlist**: Restricting to A-Z0-9 improves accuracy
- **Test-time Augmentation**: Multiple rotations help with angled images
- **ROI Detection**: Focusing on regions with text-like features improves accuracy

### Apple Silicon Integration

The project includes a custom adapter for EasyOCR to use Apple Silicon's GPU capabilities through PyTorch's MPS (Metal Performance Shaders) backend. This provides significant performance benefits on M1/M2/M3 Macs without affecting compatibility with other platforms.

## Future Enhancements

1. **Advanced Validation**: Real-time Apple API integration
2. **Batch Processing**: Handle hundreds of serials simultaneously
3. **Advanced Analytics**: Processing statistics and reporting
4. **Enterprise Security**: User management, audit logging
5. **Performance Monitoring**: System health dashboards

## Project Structure

```
apple-ocr-backend/           # Backend service
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration
│   ├── pipeline/            # OCR processing pipeline
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   └── utils/               # Helper functions
└── docs/
    └── frontend-details/    # iOS frontend documentation

apple-ocr-ios-app/           # iOS frontend (planned)
├── AppleSerialOCR/
│   ├── Views/               # SwiftUI views
│   ├── Models/              # Data models
│   ├── Services/            # Business logic
│   └── Utils/               # Helper functions
└── AppleSerialOCRTests/     # Unit tests
```

## Key Memories from Development

1. Created exported-assets/labels.csv with columns filename,serial for accuracy evaluation
2. Implemented various OCR improvements:
   - 2x upscaling in preprocessing
   - Inverted image OCR pass
   - Allowlist A-Z0-9
   - Tuned EasyOCR parameters (low_text, text_threshold, mag_ratio)
3. Added API tunables for improving OCR on real images:
   - thresh_block_size
   - thresh_C
   - morph_kernel
   - upscale_scale
   - low_text
   - text_threshold
4. Remaining TODOs:
   - Finalize param_sweep quick mode
   - Add auto glare/illumination heuristic
   - Improve ROI band detector thresholds
   - Re-run benchmark + CSV report
   - Verify GPU path end-to-end

## Integration Strategy

The iOS frontend will communicate with the backend through a RESTful API:

1. **Image Upload**: POST /process-serial with multipart/form-data
2. **Parameter Control**: Query parameters for preset and device_type
3. **Result Handling**: JSON response with serial number and confidence
4. **Health Checks**: GET /health to monitor backend availability

## Conclusion

This Apple OCR project represents a comprehensive solution for capturing and processing Apple device serial numbers. By combining a specialized OCR backend with an intuitive iOS frontend, the system aims to provide high accuracy and a smooth user experience for both individual users and enterprise environments.

The detailed documentation created for the frontend development will guide the implementation process, ensuring alignment with the backend capabilities and overall project goals.

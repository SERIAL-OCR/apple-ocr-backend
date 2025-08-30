# Phase 2.4 Smoke Testing Guide

## Overview
This guide provides step-by-step instructions for smoke testing the Apple Serial Scanner app on real iOS devices and macOS systems to verify Phase 2.4 implementation.

## Prerequisites

### Backend Setup
1. **Start the FastAPI backend server:**
   ```bash
   cd /path/to/apple-ocr-backend
   python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "healthy", "phase": "2.1", ...}`

### Xcode Project Setup
1. **Create new Xcode project:**
   - Open Xcode
   - Create new project → iOS → App
   - Product Name: `AppleSerialScanner`
   - Interface: SwiftUI
   - Language: Swift
   - Include Tests: No

2. **Add macOS target:**
   - File → New → Target
   - macOS → App
   - Product Name: `AppleSerialScanner`
   - Interface: SwiftUI
   - Language: Swift

3. **Copy files from our implementation:**
   - Copy all files from `ios/AppleSerialScanner/AppleSerialScanner/` to your Xcode project
   - Ensure both iOS and macOS targets include all files
   - Update Info.plist for camera permissions

## iOS Smoke Testing

### Test 1: Basic Camera Functionality
**Objective:** Verify camera access and preview
**Steps:**
1. Launch app on iOS device
2. Grant camera permissions when prompted
3. Verify camera preview appears
4. Verify ROI overlay (auto-square) is visible
5. Verify corner indicators are present

**Expected Results:**
- Camera preview displays correctly
- ROI overlay appears as a square with corner indicators
- No crashes or permission errors

### Test 2: Auto-Scan Functionality
**Objective:** Test automatic serial number detection
**Steps:**
1. Point camera at a MacBook serial number
2. Position serial within the ROI square
3. Wait for auto-scan (2-4 seconds)
4. Verify early stopping when confidence ≥0.85

**Expected Results:**
- Auto-scan triggers within 2-4 seconds
- Serial number detected and displayed
- Early stopping works when high confidence achieved
- Processing time ≤4 seconds

### Test 3: Manual Capture
**Objective:** Test manual photo capture
**Steps:**
1. Point camera at serial number
2. Tap manual capture button
3. Verify photo is captured and processed

**Expected Results:**
- Manual capture works
- Processing completes within 4 seconds
- Results displayed correctly

### Test 4: Client-Side Validation
**Objective:** Test AppleSerialValidator integration
**Steps:**
1. Scan various serial numbers:
   - Valid Apple serial (e.g., C02ABCD12345)
   - Invalid format (e.g., ABC123)
   - Known prefix (e.g., C02, DNP, etc.)
   - Unknown prefix (e.g., ZZZ123456789)

**Expected Results:**
- Valid serials: Accepted with high confidence
- Invalid formats: Rejected with validation message
- Known prefixes: Position corrections applied
- Unknown prefixes: Lower confidence, borderline status

### Test 5: Backend Submission
**Objective:** Test submission to backend
**Steps:**
1. Configure backend URL in Settings
2. Enter valid API key
3. Scan a valid serial number
4. Verify submission to backend

**Expected Results:**
- Settings save correctly
- Connection test passes
- Serial submitted to backend successfully
- Response received and handled

### Test 6: Settings and Configuration
**Objective:** Test settings functionality
**Steps:**
1. Open Settings tab
2. Change backend URL
3. Enter API key
4. Test connection
5. Change preset (Default/Accessory)
6. View device info

**Expected Results:**
- Settings save and persist
- Connection test works
- Preset changes affect ROI and guidance
- Device info displays correctly

### Test 7: History and Export
**Objective:** Test history viewing and export
**Steps:**
1. Open History tab
2. Verify recent scans display
3. Test filtering (source, status, date)
4. Test search functionality
5. Trigger export

**Expected Results:**
- History displays correctly
- Filters work as expected
- Search finds relevant results
- Export generates Excel file

## macOS Smoke Testing

### Test 1: Webcam Access
**Objective:** Verify webcam functionality
**Steps:**
1. Launch app on Mac
2. Grant camera permissions
3. Verify webcam preview appears
4. Verify ROI overlay is visible

**Expected Results:**
- Webcam preview displays
- ROI overlay appears correctly
- No permission errors

### Test 2: Cross-Platform Consistency
**Objective:** Verify same functionality as iOS
**Steps:**
1. Perform all iOS tests on macOS
2. Compare behavior and UI

**Expected Results:**
- Same functionality as iOS
- Platform-appropriate UI adaptations
- Consistent validation and submission

### Test 3: Export Functionality
**Objective:** Test enhanced export features
**Steps:**
1. Generate multiple scans
2. Test export with various filters
3. Verify Excel file generation
4. Check file formatting and metadata

**Expected Results:**
- Export works with all filters
- Excel file properly formatted
- Metadata includes filter information
- File naming includes filter details

## Performance Testing

### Latency Measurements
**Objective:** Verify 2-4 second scan times
**Steps:**
1. Use stopwatch to measure scan time
2. Test with various lighting conditions
3. Test with different serial number positions
4. Record average and P95 times

**Expected Results:**
- Average scan time: 2-4 seconds
- P95 scan time: ≤6 seconds
- Early stopping reduces average time

### Accuracy Testing
**Objective:** Verify ≥95% accuracy target
**Steps:**
1. Test with known good serial numbers
2. Test with challenging conditions (glare, angle, etc.)
3. Record success/failure rates
4. Calculate accuracy percentage

**Expected Results:**
- Accuracy ≥95% on good conditions
- Graceful degradation on challenging conditions
- Clear feedback on failures

## Error Handling Testing

### Network Issues
**Objective:** Test offline/network error handling
**Steps:**
1. Disconnect network
2. Attempt to submit serial
3. Reconnect and verify retry

**Expected Results:**
- Graceful error handling
- Clear error messages
- Retry functionality works

### Invalid Data
**Objective:** Test validation error handling
**Steps:**
1. Submit invalid serial formats
2. Test with corrupted data
3. Verify error messages

**Expected Results:**
- Clear validation error messages
- No crashes or undefined behavior
- Proper error recovery

## Success Criteria

### Phase 2.4 Completion Checklist
- [ ] iOS app launches without crashes
- [ ] Camera/webcam access works
- [ ] Auto-scan functionality works (2-4s)
- [ ] Manual capture works
- [ ] Client-side validation works
- [ ] Backend submission works
- [ ] Settings configuration works
- [ ] History and export work
- [ ] Cross-platform consistency verified
- [ ] Performance targets met (latency, accuracy)
- [ ] Error handling works properly

### Production Readiness
- [ ] All smoke tests pass
- [ ] Performance targets achieved
- [ ] Error handling robust
- [ ] User experience smooth
- [ ] Backend integration stable
- [ ] Export functionality complete

## Troubleshooting

### Common Issues
1. **Camera not working:** Check permissions in Settings
2. **Backend connection failed:** Verify server is running and URL is correct
3. **Slow performance:** Check device capabilities and lighting
4. **Validation errors:** Verify serial number format and positioning

### Debug Information
- Check Xcode console for errors
- Verify backend logs for submission issues
- Test with known good serial numbers
- Verify network connectivity

## Next Steps
After successful smoke testing:
1. Document any issues found
2. Implement fixes for critical issues
3. Prepare for client data intake workflow
4. Plan Phase 2.5 development (evaluation mode)
5. Create deployment guide for production

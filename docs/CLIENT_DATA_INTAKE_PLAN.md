# Client Data Intake and Evaluation Plan

## Overview
This document outlines the workflow for receiving, processing, and evaluating client-provided Apple device serial images to improve our OCR system accuracy.

## Data Intake Process

### 1. Client Submission Format

**Required Package Structure:**
```
client_data_batch_YYYYMMDD.zip
├── images/
│   ├── macbook_001.jpg
│   ├── macbook_002.jpg
│   ├── iphone_001.jpg
│   ├── airpods_001.jpg
│   └── ...
├── labels.csv
└── metadata.json (optional)
```

**Labels CSV Format:**
```csv
filename,serial,device_type,notes
macbook_001.jpg,C02ABCD1234E,macbook,clean image
macbook_002.jpg,,macbook,unknown serial
iphone_001.jpg,DNPP12345678,iphone,good lighting
airpods_001.jpg,,airpods,blurry image
```

### 2. Privacy and Consent

**Client Agreement Required:**
- Images used only for on-device evaluation and algorithm tuning
- No PII uploaded to any server
- OCR processing happens entirely on-device
- Images may be stored locally for evaluation purposes
- Client retains ownership of all images

**Consent Template:**
```
I understand that:
1. Images will be processed on-device only (no cloud upload)
2. Images may be stored locally for evaluation
3. No personal information will be extracted or stored
4. Images are used solely to improve OCR accuracy
5. I can request deletion of my images at any time
```

### 3. Data Ingestion Workflow

#### Step 1: Receive and Validate
```bash
# Extract client data
unzip client_data_batch_YYYYMMDD.zip -d temp_client_data/

# Validate structure
python scripts/validate_client_data.py temp_client_data/
```

#### Step 2: Process and Store
```bash
# Copy images to exported-assets/
cp temp_client_data/images/* exported-assets/

# Merge labels into main labels.csv
python scripts/merge_labels.py temp_client_data/labels.csv exported-assets/labels.csv
```

#### Step 3: Quality Assurance
- **Spot Check:** Review 10-20% of labeled images for obvious errors
- **Pattern Validation:** Verify serial number formats match Apple patterns
- **Image Quality:** Flag images that may need preprocessing

### 4. Storage and Organization

**Directory Structure:**
```
exported-assets/
├── labels.csv                    # Master labels file
├── client_batches/              # Organized by client/batch
│   ├── client_a_batch_001/
│   │   ├── images/
│   │   ├── labels.csv
│   │   └── metadata.json
│   └── client_b_batch_001/
├── evaluation_results/          # Evaluation outputs
│   ├── eval_20250101_120000.csv
│   ├── eval_20250101_140000.csv
│   └── ...
└── debug_images/               # Failed detection debug images
    ├── no_detection_001.png
    └── low_confidence_001.png
```

**Labels CSV Schema:**
```csv
filename,serial,device_type,source,date_added,quality_score,notes
macbook_001.jpg,C02ABCD1234E,macbook,client_a,2025-01-01,0.9,clean image
macbook_002.jpg,,macbook,client_a,2025-01-01,0.7,unknown serial
```

## On-Device Evaluation Mode

### 1. App Configuration

**Settings → Evaluation Mode:**
- [ ] Enable Evaluation Mode
- [ ] Submit accepted results to backend
- [ ] Save debug images locally
- [ ] Export detailed CSV reports

### 2. Batch Processing Workflow

#### iOS Evaluation Flow:
1. **Import Images:**
   - Files app integration
   - Select folder containing images
   - Validate image formats (JPG, PNG, HEIC)

2. **Batch Processing:**
   - Process each image with Vision OCR
   - Apply AppleSerialValidator
   - Track confidence scores and validation results

3. **Results Display:**
   - Progress indicator
   - Per-image results table
   - Summary statistics

4. **Export Results:**
   - CSV export with detailed results
   - Debug images for failed detections
   - Share via Files app

#### macOS Evaluation Flow:
1. **Folder Selection:**
   - Native folder picker
   - Drag-and-drop support
   - Recursive folder scanning

2. **Processing:**
   - Same Vision OCR pipeline as iOS
   - Parallel processing for faster results
   - Real-time progress updates

3. **Results Management:**
   - In-app results viewer
   - Filter and sort capabilities
   - Export to multiple formats

### 3. Evaluation Output Format

**Detailed CSV Report:**
```csv
filename,predicted_serial,corrected_serial,ground_truth,confidence,validation_level,device_type,preset,processing_ms,accepted,notes
macbook_001.jpg,C02ABCD1234E,C02ABCD1234E,C02ABCD1234E,0.95,ACCEPT,macbook,default,1200,true,exact match
macbook_002.jpg,C02ABCD1234F,C02ABCD1234E,,0.87,BORDERLINE,macbook,default,1100,false,correction applied
iphone_001.jpg,DNPP12345678,DNPP12345678,DNPP12345678,0.92,ACCEPT,iphone,default,950,true,exact match
```

**Summary Statistics:**
```json
{
  "total_images": 100,
  "detection_rate": 0.95,
  "acceptance_rate": 0.88,
  "average_confidence": 0.91,
  "device_type_breakdown": {
    "macbook": {"count": 50, "detection_rate": 0.96},
    "iphone": {"count": 30, "detection_rate": 0.93},
    "airpods": {"count": 20, "detection_rate": 0.90}
  },
  "validation_breakdown": {
    "ACCEPT": 88,
    "BORDERLINE": 7,
    "REJECT": 5
  }
}
```

## Implementation Tasks

### Backend Tasks
- [ ] Create `/api/evaluation/upload` endpoint for batch results
- [ ] Add evaluation mode configuration to `/api/config`
- [ ] Implement evaluation statistics aggregation
- [ ] Create evaluation report generation endpoint

### iOS Tasks
- [ ] Add evaluation mode toggle to Settings
- [ ] Implement Files app integration for image import
- [ ] Create batch processing UI with progress
- [ ] Add results viewer and export functionality
- [ ] Implement debug image saving

### macOS Tasks
- [ ] Add evaluation mode toggle to Settings
- [ ] Implement folder picker and drag-drop
- [ ] Create batch processing with parallel execution
- [ ] Add comprehensive results viewer
- [ ] Implement multi-format export

### Shared Tasks
- [ ] Create evaluation data models
- [ ] Implement batch processing logic
- [ ] Add evaluation statistics calculation
- [ ] Create CSV export utilities

## Quality Metrics

### Detection Rate
- Percentage of images where OCR detected any text
- Target: >95% for good quality images

### Accuracy Rate
- Percentage of detected serials that match ground truth
- Target: >90% for known serials

### Acceptance Rate
- Percentage of detections that pass validation
- Target: >85% for production use

### Confidence Distribution
- Track confidence score distribution
- Identify optimal confidence thresholds

## Continuous Improvement

### Data-Driven Tuning
1. **Analyze failures:** Review images with low detection/accuracy
2. **Adjust parameters:** Tune ROI, text height, confidence thresholds
3. **Test improvements:** Re-run evaluation on same dataset
4. **Track progress:** Monitor metrics over time

### Model Updates
1. **Collect edge cases:** Identify challenging image types
2. **Generate synthetic data:** Create variations of difficult cases
3. **Retrain if needed:** Consider custom Vision model fine-tuning
4. **Validate improvements:** Test on held-out dataset

## Security and Privacy

### Data Handling
- All processing on-device only
- No image uploads to external servers
- Local storage with encryption at rest
- Automatic cleanup of old evaluation data

### Access Control
- Evaluation mode requires explicit user consent
- Results export requires user action
- Debug images only saved when explicitly enabled

### Compliance
- GDPR compliance for EU clients
- CCPA compliance for California clients
- Data retention policies (30 days for evaluation data)
- Right to deletion for all client data

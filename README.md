# Apple Serial Number OCR Backend

A high-performance OCR backend system for detecting and processing Apple device serial numbers from images. Built with FastAPI, EasyOCR, and YOLO for optimal accuracy and speed.

## 🚀 Features

- **High-Performance OCR**: Multi-stage processing pipeline with early stopping
- **Apple Silicon Optimized**: GPU acceleration using PyTorch MPS
- **Background Processing**: Asynchronous job processing with real-time progress
- **Hybrid Fallback**: EasyOCR + Tesseract for maximum detection rates
- **Quality Filtering**: Intelligent confidence scoring and result validation
- **Excel Export**: Automatic report generation with timestamped exports
- **Production Ready**: Docker deployment with health checks and monitoring

## 📊 Performance

- **Fast Processing**: 60-70% of scans complete in 4-8 seconds
- **High Accuracy**: 85-90% detection rate with confidence scoring
- **Early Stopping**: Intelligent pipeline optimization for speed
- **Scalable**: Background job processing with queue management

## 🏗️ Architecture

```
iOS App → API Submission → Background Processing → Database Storage → Excel Export
```

### Processing Pipeline:
1. **Stage 1**: Fast YOLO ROI detection + basic OCR (4.3s)
2. **Stage 2**: Enhanced preprocessing + inverted image (4.5s)
3. **Stage 3**: Full multi-scale processing (8.0s)
4. **Stage 4**: Hybrid fallback with Tesseract (46.5s worst case)

## 🛠️ Quick Start

### **New Users** 
Start here: **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Complete setup guide for new users

### **Quick Start (2 minutes)**
```bash
git clone https://github.com/SERIAL-OCR/apple-ocr-backend.git
cd apple-ocr-backend
chmod +x scripts/deploy.sh
./scripts/deploy.sh dev
curl http://localhost:8000/health
```

### Prerequisites

- Docker and Docker Compose
- Apple Silicon Mac (M1/M2/M3) for optimal performance
- 4GB+ RAM recommended

### Development Setup

1. **Clone the repository:**
```bash
git clone <repository-url>
cd apple-ocr-backend
```

2. **Start development environment:**
```bash
docker compose up --build
```

3. **Access the API:**
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

### Production Deployment

1. **Deploy with production settings:**
```bash
docker compose -f docker-compose.prod.yml up --build -d
```

2. **Monitor the deployment:**
```bash
docker compose -f docker-compose.prod.yml logs -f
```

## 📁 Project Structure

```
apple-ocr-backend/
├── app/                          # Main application code
│   ├── main.py                   # FastAPI application entry point
│   ├── config.py                 # Configuration management
│   ├── db.py                     # Database operations
│   ├── pipeline/                 # OCR processing pipeline
│   │   ├── ocr_adapter_improved.py  # Main OCR processing
│   │   ├── yolo_detector.py      # YOLO ROI detection
│   │   └── tesseract_adapter.py  # Tesseract fallback
│   ├── routers/                  # API endpoints
│   │   └── serials.py            # Serial processing endpoints
│   ├── services/                 # Business logic services
│   └── utils/                    # Utility functions
├── storage/                      # Persistent data storage
│   ├── database/                 # SQLite database files
│   ├── exports/                  # Excel export files
│   ├── logs/                     # Application logs
│   └── backups/                  # Database backups
├── scripts/                      # Utility scripts
├── tests/                        # Test suite
├── docker-compose.yml            # Development Docker setup
├── docker-compose.prod.yml       # Production Docker setup
└── Dockerfile                    # Docker image definition
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PRODUCTION_MODE` | `false` | Enable production optimizations |
| `ENABLE_TESSERACT_FALLBACK` | `true` | Enable Tesseract fallback OCR |
| `MAX_PROCESSING_TIME` | `30.0` | Maximum processing time in seconds |
| `EARLY_STOP_CONFIDENCE` | `0.65` | Confidence threshold for early stopping |
| `USE_GPU` | `true` | Enable GPU acceleration |
| `PYTORCH_MPS_HIGH_WATERMARK_RATIO` | `0.0` | MPS memory management |
| `OCR_BATCH_SIZE` | `4` | OCR batch processing size |

### Development vs Production

| Setting | Development | Production |
|---------|-------------|------------|
| Mode | `PRODUCTION_MODE=false` | `PRODUCTION_MODE=true` |
| Early Stop Confidence | `0.65` | `0.65` |
| Max Processing Time | `30.0s` | `35.0s` |
| Reload | `true` | `false` |
| Workers | `1` | `1` |
| Memory Limit | None | `4GB` |

## 📡 API Endpoints

### Core Endpoints

- `POST /scan` - Submit image for OCR processing
- `GET /result/{job_id}` - Get processing results
- `GET /jobs` - List all jobs
- `DELETE /jobs/{job_id}` - Delete a job
- `GET /export` - Generate Excel export
- `GET /health` - Health check

### Processing Endpoints

- `POST /process-serial` - Legacy direct processing
- `GET /params` - Get cached parameters
- `POST /params/sweep` - Trigger parameter optimization
- `GET /evaluate` - Evaluate processing on test images

## 🔍 Usage Examples

### Submit a Scan

```bash
curl -X POST "http://localhost:8000/scan" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@image.jpg" \
  -F "device_type=iphone"
```

### Check Job Status

```bash
curl "http://localhost:8000/result/{job_id}"
```

### Generate Excel Export

```bash
curl "http://localhost:8000/export" --output report.xlsx
```

## 🧪 Testing

### Run Test Suite

```bash
# Run all tests
python -m pytest tests/

# Run specific test categories
python -m pytest tests/unit/
python -m pytest tests/smoke/
```

### Performance Testing

```bash
# Run performance analysis
python scripts/performance_analysis.py --image "path/to/test/image.jpg"
```

## 📈 Monitoring

### Health Checks

The application includes built-in health checks:

```bash
curl http://localhost:8000/health
```

### Logs

```bash
# View application logs
docker compose logs -f api

# View production logs
docker compose -f docker-compose.prod.yml logs -f
```

### Storage Monitoring

```bash
# Check storage usage
ls -la storage/
du -sh storage/*
```

## 🔧 Troubleshooting

### Common Issues

1. **GPU Not Available**
   - Ensure you're on Apple Silicon Mac
   - Check PyTorch MPS installation
   - Verify GPU memory settings

2. **Slow Processing**
   - Check image quality and size
   - Monitor memory usage
   - Verify early stopping configuration

3. **Low Confidence Results**
   - Adjust confidence thresholds
   - Check image preprocessing
   - Verify OCR parameters

### Debug Mode

Enable debug logging:

```bash
docker compose up -e LOG_LEVEL=DEBUG
```

## 📚 Documentation

- [Performance Analysis](PERFORMANCE_ANALYSIS_SUMMARY.md)
- [Preprocessing Optimization](PREPROCESSING_OPTIMIZATION_SUMMARY.md)
- [Confidence Optimization](CONFIDENCE_OPTIMIZATION_SUMMARY.md)
- [Storage Migration](STORAGE_MIGRATION_SUMMARY.md)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the documentation

---

**Status**: ✅ Production Ready - Optimized for Apple Silicon with high-performance OCR processing.

# 🚀 Apple OCR Backend - New User Setup Guide

Welcome to the Apple OCR Backend project! This guide will help you get started quickly and easily.

## 📋 Prerequisites

Before you begin, make sure you have the following installed:

### **Required Software**
- **Docker Desktop** - [Download here](https://www.docker.com/products/docker-desktop)
- **Git** - [Download here](https://git-scm.com/downloads)
- **macOS** (Apple Silicon Mac recommended for best performance)

### **System Requirements**
- **RAM**: 4GB minimum, 8GB+ recommended
- **Storage**: 10GB+ free space
- **Processor**: Apple Silicon (M1/M2/M3) for optimal performance

## 🛠️ Quick Start (5 Minutes)

### **Step 1: Clone the Repository**
```bash
# Clone the project
git clone https://github.com/SERIAL-OCR/apple-ocr-backend.git

# Navigate to the project directory
cd apple-ocr-backend
```

### **Step 2: Start the Application**
```bash
# Make the deployment script executable
chmod +x scripts/deploy.sh

# Deploy the development environment
./scripts/deploy.sh dev
```

### **Step 3: Verify Installation**
```bash
# Check if the service is running
./scripts/deploy.sh status

# Test the API
curl http://localhost:8000/health
```

### **Step 4: Access the Application**
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

🎉 **Congratulations! Your Apple OCR Backend is now running!**

## 📱 Testing the Application

### **Test with a Sample Image**
```bash
# Test with a sample image (if available)
curl -X POST "http://localhost:8000/scan" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@Apple serial/IMG-20250813-WA0025.jpg" \
  -F "device_type=iphone"
```

### **Generate an Excel Report**
```bash
# Download the latest Excel report
curl "http://localhost:8000/export" --output report.xlsx
```

## 🔧 Detailed Setup Options

### **Option A: Development Environment (Recommended for New Users)**
```bash
# Start development environment with hot reload
docker compose up --build -d

# View logs
docker compose logs -f
```

### **Option B: Production Environment**
```bash
# Start production environment
docker compose -f docker-compose.prod.yml up --build -d

# View production logs
docker compose -f docker-compose.prod.yml logs -f
```

### **Option C: Manual Setup (Advanced Users)**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On macOS/Linux
# .venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📁 Project Structure Overview

```
apple-ocr-backend/
├── app/                    # Main application code
├── storage/                # Data storage (created automatically)
│   ├── database/          # Database files
│   ├── exports/           # Excel reports
│   ├── logs/              # Application logs
│   └── backups/           # Database backups
├── scripts/               # Utility scripts
├── tests/                 # Test files
├── docker-compose.yml     # Development setup
├── docker-compose.prod.yml # Production setup
└── README.md              # Main documentation
```

## 🎯 What You Can Do

### **1. Process Apple Serial Numbers**
- Upload images containing Apple device serial numbers
- Get automatic OCR processing results
- View confidence scores and validation

### **2. Generate Reports**
- Export processed serials to Excel
- View processing history
- Track accuracy metrics

### **3. Monitor Performance**
- Check processing speed
- View system health
- Monitor resource usage

## 🔍 Common Commands

### **Management Commands**
```bash
# Check service status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs dev      # Development logs
./scripts/deploy.sh logs prod     # Production logs

# Stop services
./scripts/deploy.sh stop

# Run tests
./scripts/deploy.sh test
```

### **Docker Commands**
```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# Rebuild and start
docker compose up --build -d

# View logs
docker compose logs -f
```

## 🚨 Troubleshooting

### **Issue: "Docker not found"**
**Solution**: Install Docker Desktop from [docker.com](https://www.docker.com/products/docker-desktop)

### **Issue: "Port 8000 already in use"**
**Solution**: 
```bash
# Find what's using port 8000
lsof -i :8000

# Stop the conflicting service or use a different port
```

### **Issue: "Permission denied"**
**Solution**:
```bash
# Make scripts executable
chmod +x scripts/deploy.sh

# Fix storage permissions
chmod -R 755 storage/
```

### **Issue: "Service won't start"**
**Solution**:
```bash
# Check logs
docker compose logs

# Check system resources
docker system df

# Restart Docker Desktop
```

### **Issue: "Low performance"**
**Solutions**:
- Ensure you're on Apple Silicon Mac
- Close other resource-intensive applications
- Check available RAM (should be 4GB+)
- Verify GPU acceleration is working

## 📊 Performance Expectations

### **Processing Speed**
- **Fast scans**: 4-8 seconds (60-70% of cases)
- **Average scans**: 8-12 seconds
- **Challenging scans**: 30-60 seconds

### **Accuracy**
- **Detection rate**: 85-90%
- **Confidence scoring**: Intelligent quality assessment
- **Fallback processing**: Multiple OCR engines

## 🔗 Useful Links

### **API Documentation**
- **Interactive Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### **Project Documentation**
- [Main README](README.md) - Complete project overview
- [Docker Deployment Guide](DOCKER_DEPLOYMENT_GUIDE.md) - Advanced deployment
- [Performance Analysis](PERFORMANCE_ANALYSIS_SUMMARY.md) - Performance details

## 🆘 Getting Help

### **If Something Goes Wrong**
1. **Check the logs**: `./scripts/deploy.sh logs dev`
2. **Verify status**: `./scripts/deploy.sh status`
3. **Run tests**: `./scripts/deploy.sh test`
4. **Check documentation**: Review the guides above

### **Common Questions**

**Q: How do I update the application?**
```bash
git pull origin main
./scripts/deploy.sh dev
```

**Q: How do I backup my data?**
```bash
# Backup database
cp storage/database/app.db storage/backups/app_$(date +%Y%m%d_%H%M%S).db

# Backup exports
cp storage/exports/*.xlsx storage/backups/
```

**Q: How do I change configuration?**
Edit the environment variables in `docker-compose.yml` or `docker-compose.prod.yml`

## 🎉 Next Steps

Once you have the application running:

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Test with images**: Try uploading some Apple device images
3. **Generate reports**: Export Excel reports of processed serials
4. **Monitor performance**: Check processing speed and accuracy
5. **Read the documentation**: Explore the detailed guides

---

**Need help?** Check the troubleshooting section above or review the main documentation.

**Status**: ✅ **Ready to Use** - Your Apple OCR Backend is now set up and ready for processing Apple device serial numbers!

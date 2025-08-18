# 🐳 Docker Setup Guide for Apple OCR Backend

## 📋 **Prerequisites**

- Docker installed on your system
- Docker Compose installed
- At least 4GB RAM available for the container

## 🚀 **Quick Start**

### **Development Mode (Recommended for Testing)**

```bash
# Build and start the development container
docker-compose up --build

# Or run in background
docker-compose up -d --build
```

### **Production Mode**

```bash
# Build and start the production container
docker-compose -f docker-compose.prod.yml up --build

# Or run in background
docker-compose -f docker-compose.prod.yml up -d --build
```

## 📁 **Persistent Storage**

The following directories are mounted as volumes for data persistence:

- **`./data/`** → Database storage (SQLite)
- **`./exports/`** → Excel export files
- **`./logs/`** → Application logs

## 🔧 **Environment Variables**

### **Development Mode**
- `PRODUCTION_MODE=false`
- `ENABLE_TESSERACT_FALLBACK=true`
- `MAX_PROCESSING_TIME=30.0`
- `EARLY_STOP_CONFIDENCE=0.3`
- `USE_GPU=true`

### **Production Mode**
- `PRODUCTION_MODE=true`
- `ENABLE_TESSERACT_FALLBACK=true`
- `MAX_PROCESSING_TIME=35.0`
- `EARLY_STOP_CONFIDENCE=0.75`
- `USE_GPU=true`

## 📊 **Database Storage**

### **Local Database Location**
- **Path**: `./data/app.db`
- **Type**: SQLite database
- **Persistence**: Survives container restarts

### **Database Schema**
```sql
CREATE TABLE serials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    serial TEXT NOT NULL,
    device_type TEXT,
    confidence REAL
);
```

## 📤 **Export Functionality**

### **Excel Export Location**
- **Path**: `./exports/`
- **Format**: `serials_YYYYMMDD_HHMMSS.xlsx`
- **Content**: All scanned serial numbers with metadata

### **Accessing Exports**
```bash
# List export files
ls -la exports/

# Download latest export
curl -o latest_export.xlsx http://localhost:8000/export
```

## 🔍 **Monitoring & Health Checks**

### **Health Check Endpoint**
```bash
# Check if service is running
curl http://localhost:8000/health

# Expected response
{
    "status": "ok",
    "gpu": {
        "torch_present": true,
        "cuda_available": false,
        "device_count": 0,
        "use_gpu_config": true
    }
}
```

### **Container Logs**
```bash
# View logs
docker-compose logs -f api

# View last 100 lines
docker-compose logs --tail=100 api
```

## 🛠️ **Management Commands**

### **Start Services**
```bash
# Development
docker-compose up

# Production
docker-compose -f docker-compose.prod.yml up
```

### **Stop Services**
```bash
# Development
docker-compose down

# Production
docker-compose -f docker-compose.prod.yml down
```

### **Rebuild After Changes**
```bash
# Development
docker-compose up --build

# Production
docker-compose -f docker-compose.prod.yml up --build
```

### **View Running Containers**
```bash
docker ps
```

### **Access Container Shell**
```bash
# Development
docker-compose exec api bash

# Production
docker-compose -f docker-compose.prod.yml exec api bash
```

## 📱 **Testing the API**

### **Test Scan Submission**
```bash
# Submit a scan
curl -X POST http://localhost:8000/scan \
  -F "image=@Apple serial/IMG-20250813-WA0034.jpg" \
  -F "device_type=macbook"
```

### **Check Queue Status**
```bash
# Get queue information
curl http://localhost:8000/queue/status
```

### **Get Scan History**
```bash
# Get recent scans
curl http://localhost:8000/history
```

### **Export Data**
```bash
# Download Excel export
curl -o export.xlsx http://localhost:8000/export
```

## 🔧 **Troubleshooting**

### **Container Won't Start**
```bash
# Check logs
docker-compose logs api

# Check if port is in use
lsof -i :8000

# Remove and rebuild
docker-compose down
docker-compose up --build
```

### **Database Issues**
```bash
# Check database file
ls -la data/

# Reset database (WARNING: Deletes all data)
rm data/app.db
docker-compose restart api
```

### **Export Issues**
```bash
# Check exports directory
ls -la exports/

# Create directory if missing
mkdir -p exports
```

### **Memory Issues**
```bash
# Check container memory usage
docker stats

# Increase memory limit in docker-compose.yml
```

## 📈 **Performance Optimization**

### **Development Mode**
- Hot reload enabled
- Single worker process
- Lower memory limits
- Faster startup

### **Production Mode**
- No hot reload
- Optimized for performance
- Higher memory limits
- Health checks enabled

## 🔒 **Security Considerations**

### **Development**
- All origins allowed (CORS)
- Debug mode enabled
- Detailed error messages

### **Production**
- Restrict CORS origins
- Disable debug mode
- Minimal error messages
- Resource limits enforced

## 📋 **Deployment Checklist**

- [ ] Database directory exists (`./data/`)
- [ ] Exports directory exists (`./exports/`)
- [ ] Logs directory exists (`./logs/`)
- [ ] Port 8000 available
- [ ] Sufficient memory (4GB+)
- [ ] GPU drivers installed (for MPS acceleration)

## 🎯 **Next Steps**

1. **Test locally** with development mode
2. **Verify database persistence** across restarts
3. **Test export functionality** with multiple scans
4. **Deploy to production** when ready
5. **Monitor performance** and adjust resources as needed

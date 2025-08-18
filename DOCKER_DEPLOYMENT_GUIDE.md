# Docker Deployment Guide

Complete guide for deploying the Apple OCR Backend using Docker and Docker Compose.

## 🐳 Docker Configuration Overview

### Development Environment (`docker-compose.yml`)
- **Purpose**: Local development and testing
- **Features**: Hot reload, debug mode, development optimizations
- **Storage**: Unified storage structure with volume mounting

### Production Environment (`docker-compose.prod.yml`)
- **Purpose**: Production deployment
- **Features**: Optimized for performance, health checks, resource limits
- **Storage**: Persistent storage with backup capabilities

## 🚀 Quick Start

### Prerequisites

1. **Install Docker and Docker Compose**
   ```bash
   # macOS (using Homebrew)
   brew install docker docker-compose
   
   # Or download from Docker Desktop
   # https://www.docker.com/products/docker-desktop
   ```

2. **Verify Installation**
   ```bash
   docker --version
   docker compose version
   ```

3. **System Requirements**
   - Apple Silicon Mac (M1/M2/M3) for optimal performance
   - 4GB+ RAM
   - 10GB+ free disk space

## 🛠️ Development Deployment

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd apple-ocr-backend

# Verify project structure
ls -la
```

### 2. Start Development Environment

```bash
# Build and start the development environment
docker compose up --build

# Or run in background
docker compose up --build -d
```

### 3. Verify Deployment

```bash
# Check container status
docker compose ps

# Check logs
docker compose logs -f

# Test health endpoint
curl http://localhost:8000/health
```

### 4. Access Services

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **API Base URL**: http://localhost:8000

## 🏭 Production Deployment

### 1. Production Setup

```bash
# Deploy production environment
docker compose -f docker-compose.prod.yml up --build -d

# Check production status
docker compose -f docker-compose.prod.yml ps

# Monitor production logs
docker compose -f docker-compose.prod.yml logs -f
```

### 2. Production Verification

```bash
# Test health endpoint
curl http://localhost:8000/health

# Check resource usage
docker stats apple-ocr-backend-prod

# Verify storage mounting
docker exec apple-ocr-backend-prod ls -la /app/storage/
```

### 3. Production Monitoring

```bash
# Monitor logs in real-time
docker compose -f docker-compose.prod.yml logs -f api

# Check container health
docker inspect apple-ocr-backend-prod | grep Health -A 10

# Monitor resource usage
docker stats apple-ocr-backend-prod
```

## 📁 Storage Management

### Storage Structure

```
storage/
├── database/          # SQLite database files
│   └── app.db        # Main application database
├── exports/           # Generated Excel reports
│   └── *.xlsx        # Timestamped export files
├── logs/             # Application logs
│   └── *.jsonl       # Structured log files
└── backups/          # Database backups
```

### Storage Operations

```bash
# View storage contents
ls -la storage/

# Check storage usage
du -sh storage/*

# Backup database
cp storage/database/app.db storage/backups/app_$(date +%Y%m%d_%H%M%S).db

# Clean old exports (keep last 10)
ls -t storage/exports/*.xlsx | tail -n +11 | xargs rm -f
```

## 🔧 Configuration Management

### Environment Variables

#### Development Configuration
```yaml
environment:
  - PRODUCTION_MODE=false
  - ENABLE_TESSERACT_FALLBACK=true
  - MAX_PROCESSING_TIME=30.0
  - EARLY_STOP_CONFIDENCE=0.65
  - USE_GPU=true
  - PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
  - OCR_BATCH_SIZE=4
```

#### Production Configuration
```yaml
environment:
  - PRODUCTION_MODE=true
  - ENABLE_TESSERACT_FALLBACK=true
  - MAX_PROCESSING_TIME=35.0
  - EARLY_STOP_CONFIDENCE=0.65
  - USE_GPU=true
  - PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0
  - OCR_BATCH_SIZE=4
  - HOST=0.0.0.0
  - PORT=8000
  - RELOAD=false
```

### Custom Configuration

Create a custom environment file:

```bash
# Create .env file
cat > .env << EOF
PRODUCTION_MODE=true
MAX_PROCESSING_TIME=40.0
EARLY_STOP_CONFIDENCE=0.70
USE_GPU=true
EOF

# Use with docker compose
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

## 🔍 Monitoring and Debugging

### Health Checks

```bash
# Manual health check
curl -f http://localhost:8000/health

# Check health status
docker inspect apple-ocr-backend-prod | grep Health -A 10
```

### Log Analysis

```bash
# View real-time logs
docker compose logs -f api

# View specific log levels
docker compose logs api | grep ERROR

# Export logs
docker compose logs api > app.log
```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats apple-ocr-backend-prod

# Check container details
docker inspect apple-ocr-backend-prod

# Monitor storage usage
du -sh storage/*
```

## 🔄 Maintenance Operations

### Container Management

```bash
# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v

# Restart services
docker compose restart

# Update and rebuild
docker compose up --build -d
```

### Data Management

```bash
# Backup database
docker exec apple-ocr-backend-prod cp /app/storage/database/app.db /app/storage/backups/

# Restore database
docker exec apple-ocr-backend-prod cp /app/storage/backups/app.db /app/storage/database/

# Clean old data
docker exec apple-ocr-backend-prod find /app/storage/exports -name "*.xlsx" -mtime +7 -delete
```

### Image Management

```bash
# List images
docker images

# Remove unused images
docker image prune

# Remove all unused resources
docker system prune -a
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Container Won't Start

```bash
# Check logs for errors
docker compose logs api

# Check resource availability
docker system df

# Verify port availability
lsof -i :8000
```

#### 2. GPU Issues

```bash
# Check GPU availability
docker exec apple-ocr-backend-prod python -c "import torch; print(torch.backends.mps.is_available())"

# Check PyTorch installation
docker exec apple-ocr-backend-prod python -c "import torch; print(torch.__version__)"
```

#### 3. Storage Issues

```bash
# Check storage permissions
ls -la storage/

# Fix permissions if needed
chmod -R 755 storage/

# Check disk space
df -h
```

#### 4. Performance Issues

```bash
# Monitor resource usage
docker stats apple-ocr-backend-prod

# Check memory usage
docker exec apple-ocr-backend-prod free -h

# Check CPU usage
docker exec apple-ocr-backend-prod top
```

### Debug Mode

Enable debug logging:

```bash
# Development debug
docker compose up -e LOG_LEVEL=DEBUG

# Production debug
docker compose -f docker-compose.prod.yml up -e LOG_LEVEL=DEBUG -d
```

## 📊 Performance Optimization

### Resource Limits

Production configuration includes resource limits:

```yaml
deploy:
  resources:
    limits:
      memory: 4G
    reservations:
      memory: 2G
```

### Optimization Tips

1. **Memory Management**
   - Monitor memory usage with `docker stats`
   - Adjust `PYTORCH_MPS_HIGH_WATERMARK_RATIO` if needed
   - Consider increasing memory limits for heavy processing

2. **Storage Optimization**
   - Regular cleanup of old export files
   - Monitor storage usage
   - Implement log rotation

3. **Network Optimization**
   - Use local networks for internal communication
   - Optimize image upload sizes
   - Consider CDN for static assets

## 🔒 Security Considerations

### Production Security

1. **Network Security**
   - Use reverse proxy (nginx) for production
   - Implement SSL/TLS encryption
   - Restrict access to management ports

2. **Container Security**
   - Run containers as non-root user
   - Regular security updates
   - Scan images for vulnerabilities

3. **Data Security**
   - Encrypt sensitive data
   - Regular backups
   - Access control for storage

## 📈 Scaling

### Horizontal Scaling

For high-traffic scenarios:

```yaml
# docker-compose.scale.yml
version: '3.8'
services:
  api:
    build: .
    deploy:
      replicas: 3
    environment:
      - WORKER_ID=${WORKER_ID}
```

### Load Balancing

Use nginx for load balancing:

```nginx
upstream ocr_backend {
    server localhost:8000;
    server localhost:8001;
    server localhost:8002;
}

server {
    listen 80;
    location / {
        proxy_pass http://ocr_backend;
    }
}
```

## 📋 Deployment Checklist

### Pre-Deployment

- [ ] Docker and Docker Compose installed
- [ ] Sufficient disk space available
- [ ] Port 8000 available
- [ ] Apple Silicon Mac for optimal performance
- [ ] 4GB+ RAM available

### Development Deployment

- [ ] Repository cloned
- [ ] `docker compose up --build` executed
- [ ] Health check passes
- [ ] API documentation accessible
- [ ] Test scan submitted successfully

### Production Deployment

- [ ] Production compose file used
- [ ] Environment variables configured
- [ ] Health checks passing
- [ ] Resource limits set
- [ ] Monitoring configured
- [ ] Backup strategy implemented

### Post-Deployment

- [ ] Performance testing completed
- [ ] Logs monitored
- [ ] Storage usage checked
- [ ] Security scan performed
- [ ] Documentation updated

---

**Status**: ✅ Production Ready - Complete Docker deployment guide with development and production configurations.

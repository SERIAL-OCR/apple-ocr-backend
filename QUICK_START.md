# ⚡ Quick Start - Apple OCR Backend

## 🚀 Get Running in 2 Minutes

```bash
# 1. Clone and enter
git clone https://github.com/SERIAL-OCR/apple-ocr-backend.git
cd apple-ocr-backend

# 2. Start the app
chmod +x scripts/deploy.sh
./scripts/deploy.sh dev

# 3. Test it works
curl http://localhost:8000/health
```

## 📱 Access Your App

- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 🔧 Essential Commands

```bash
# Check status
./scripts/deploy.sh status

# View logs
./scripts/deploy.sh logs dev

# Stop everything
./scripts/deploy.sh stop

# Run tests
./scripts/deploy.sh test
```

## 🧪 Test with Sample Image

```bash
curl -X POST "http://localhost:8000/scan" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@Apple serial/IMG-20250813-WA0025.jpg" \
  -F "device_type=iphone"
```

## 📊 Get Excel Report

```bash
curl "http://localhost:8000/export" --output report.xlsx
```

## 🚨 Quick Fixes

**Port 8000 busy?**
```bash
lsof -i :8000
```

**Permission denied?**
```bash
chmod +x scripts/deploy.sh
```

**Service won't start?**
```bash
docker compose logs
```

## 📚 Need More Help?

- **Full Setup Guide**: [SETUP_GUIDE.md](SETUP_GUIDE.md)
- **Main Documentation**: [README.md](README.md)
- **Docker Guide**: [DOCKER_DEPLOYMENT_GUIDE.md](DOCKER_DEPLOYMENT_GUIDE.md)

---

**✅ Ready to process Apple serial numbers!**

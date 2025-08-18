#!/bin/bash

# 🐳 Docker Setup Script for Apple OCR Backend
# This script helps set up Docker and deploy the backend

echo "🐳 Apple OCR Backend - Docker Setup"
echo "=================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed."
    echo ""
    echo "📋 Installation Instructions:"
    echo "1. Visit https://docs.docker.com/desktop/install/mac-install/"
    echo "2. Download Docker Desktop for Mac"
    echo "3. Install and start Docker Desktop"
    echo "4. Run this script again"
    echo ""
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running."
    echo "Please start Docker Desktop and run this script again."
    exit 1
fi

echo "✅ Docker is installed and running"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data exports logs

# Check if directories exist
if [ ! -d "data" ] || [ ! -d "exports" ] || [ ! -d "logs" ]; then
    echo "❌ Failed to create directories"
    exit 1
fi

echo "✅ Directories created successfully"

# Build the Docker image
echo "🔨 Building Docker image..."
docker compose build

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed"
    exit 1
fi

echo "✅ Docker image built successfully"

# Start the services
echo "🚀 Starting services..."
docker compose up -d

if [ $? -ne 0 ]; then
    echo "❌ Failed to start services"
    exit 1
fi

echo "✅ Services started successfully"

# Wait for service to be ready
echo "⏳ Waiting for service to be ready..."
sleep 10

# Test the API
echo "🧪 Testing API..."
response=$(curl -s http://localhost:8000/health)

if [[ $response == *"ok"* ]]; then
    echo "✅ API is working correctly"
else
    echo "❌ API test failed"
    echo "Response: $response"
    exit 1
fi

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📊 Service Information:"
echo "   API URL: http://localhost:8000"
echo "   Health Check: http://localhost:8000/health"
echo "   Queue Status: http://localhost:8000/queue/status"
echo "   History: http://localhost:8000/history"
echo "   Export: http://localhost:8000/export"
echo ""
echo "📁 Data Locations:"
echo "   Database: ./data/app.db"
echo "   Exports: ./exports/"
echo "   Logs: ./logs/"
echo ""
echo "🛠️ Management Commands:"
echo "   View logs: docker compose logs -f api"
echo "   Stop services: docker compose down"
echo "   Restart services: docker compose restart"
echo "   Update and rebuild: docker compose up --build"
echo ""
echo "📱 Ready for iOS app integration!"

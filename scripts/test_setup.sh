#!/bin/bash

# Apple OCR Backend Setup Test Script
# This script tests if the setup is working correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    print_status "Running: $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        print_success "$test_name"
        ((TESTS_PASSED++))
    else
        print_error "$test_name"
        ((TESTS_FAILED++))
    fi
}

echo "🧪 Apple OCR Backend Setup Test"
echo "================================"
echo

# Test 1: Check if we're in the right directory
run_test "Project directory structure" "[ -f 'docker-compose.yml' ] && [ -f 'scripts/deploy.sh' ]"

# Test 2: Check if Docker is installed
run_test "Docker installation" "command -v docker > /dev/null"

# Test 3: Check if Docker is running
run_test "Docker daemon running" "docker info > /dev/null"

# Test 4: Check if Docker Compose is available
run_test "Docker Compose available" "docker compose version > /dev/null"

# Test 5: Check if deployment script is executable
run_test "Deployment script executable" "[ -x 'scripts/deploy.sh' ]"

# Test 6: Check if storage directories exist
run_test "Storage directories exist" "[ -d 'storage' ]"

# Test 7: Check if storage subdirectories exist
run_test "Storage subdirectories exist" "[ -d 'storage/database' ] && [ -d 'storage/exports' ] && [ -d 'storage/logs' ] && [ -d 'storage/backups' ]"

# Test 8: Check if port 8000 is available
run_test "Port 8000 available" "! lsof -i :8000 > /dev/null 2>&1"

# Test 9: Check if curl is available
run_test "curl available" "command -v curl > /dev/null"

# Test 10: Check if Dockerfile exists
run_test "Dockerfile exists" "[ -f 'Dockerfile' ]"

# Test 11: Check if requirements.txt exists
run_test "requirements.txt exists" "[ -f 'requirements.txt' ]"

# Test 12: Check if main app file exists
run_test "Main app file exists" "[ -f 'app/main.py' ]"

echo
echo "📊 Test Results"
echo "==============="
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo "Total tests: $((TESTS_PASSED + TESTS_FAILED))"

if [ $TESTS_FAILED -eq 0 ]; then
    echo
    print_success "All tests passed! Setup is ready."
    echo
    echo "🚀 Next steps:"
    echo "1. Run: ./scripts/deploy.sh dev"
    echo "2. Check: curl http://localhost:8000/health"
    echo "3. Visit: http://localhost:8000/docs"
else
    echo
    print_error "Some tests failed. Please fix the issues above before proceeding."
    echo
    echo "🔧 Common fixes:"
    echo "- Install Docker Desktop: https://www.docker.com/products/docker-desktop"
    echo "- Start Docker Desktop"
    echo "- Make script executable: chmod +x scripts/deploy.sh"
    echo "- Check port availability: lsof -i :8000"
fi

echo
echo "📚 For more help, see: SETUP_GUIDE.md"

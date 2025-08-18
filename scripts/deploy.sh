#!/bin/bash

# Apple OCR Backend Deployment Script
# This script provides easy deployment options for development and production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if we're on Apple Silicon
    if [[ $(uname -m) != "arm64" ]]; then
        print_warning "You're not on Apple Silicon. Performance may be suboptimal."
    fi
    
    # Check available memory
    total_mem=$(sysctl -n hw.memsize | awk '{print $0/1024/1024/1024}')
    if (( $(echo "$total_mem < 4" | bc -l) )); then
        print_warning "Less than 4GB RAM detected. Performance may be affected."
    fi
    
    print_success "Prerequisites check completed"
}

# Function to create storage directories
setup_storage() {
    print_status "Setting up storage directories..."
    
    mkdir -p storage/{database,exports,logs,backups}
    
    # Set proper permissions
    chmod -R 755 storage/
    
    print_success "Storage directories created"
}

# Function to deploy development environment
deploy_dev() {
    print_status "Deploying development environment..."
    
    # Stop any existing containers
    docker compose down 2>/dev/null || true
    
    # Build and start
    docker compose up --build -d
    
    # Wait for service to be ready
    print_status "Waiting for service to be ready..."
    sleep 10
    
    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Development environment deployed successfully"
        print_status "API Documentation: http://localhost:8000/docs"
        print_status "Health Check: http://localhost:8000/health"
    else
        print_error "Service health check failed"
        docker compose logs
        exit 1
    fi
}

# Function to deploy production environment
deploy_prod() {
    print_status "Deploying production environment..."
    
    # Stop any existing containers
    docker compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    # Build and start
    docker compose -f docker-compose.prod.yml up --build -d
    
    # Wait for service to be ready
    print_status "Waiting for service to be ready..."
    sleep 15
    
    # Check health
    if curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Production environment deployed successfully"
        print_status "Health Check: http://localhost:8000/health"
    else
        print_error "Service health check failed"
        docker compose -f docker-compose.prod.yml logs
        exit 1
    fi
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    # Stop development
    docker compose down 2>/dev/null || true
    
    # Stop production
    docker compose -f docker-compose.prod.yml down 2>/dev/null || true
    
    print_success "Services stopped"
}

# Function to show logs
show_logs() {
    local env=${1:-dev}
    
    if [[ "$env" == "prod" ]]; then
        print_status "Showing production logs..."
        docker compose -f docker-compose.prod.yml logs -f
    else
        print_status "Showing development logs..."
        docker compose logs -f
    fi
}

# Function to show status
show_status() {
    print_status "Development environment status:"
    docker compose ps 2>/dev/null || echo "No development containers running"
    
    echo
    print_status "Production environment status:"
    docker compose -f docker-compose.prod.yml ps 2>/dev/null || echo "No production containers running"
    
    echo
    print_status "Storage usage:"
    du -sh storage/* 2>/dev/null || echo "Storage directory not found"
}

# Function to run tests
run_tests() {
    print_status "Running tests..."
    
    # Check if service is running
    if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
        print_error "Service is not running. Please start the service first."
        exit 1
    fi
    
    # Run basic tests
    print_status "Testing health endpoint..."
    curl -f http://localhost:8000/health
    
    print_status "Testing export endpoint..."
    curl -f http://localhost:8000/export -o /tmp/test_export.xlsx
    
    print_success "Basic tests completed"
}

# Function to show help
show_help() {
    echo "Apple OCR Backend Deployment Script"
    echo
    echo "Usage: $0 [COMMAND]"
    echo
    echo "Commands:"
    echo "  dev          Deploy development environment"
    echo "  prod         Deploy production environment"
    echo "  stop         Stop all services"
    echo "  logs [env]   Show logs (dev/prod, default: dev)"
    echo "  status       Show service status"
    echo "  test         Run basic tests"
    echo "  setup        Setup storage directories"
    echo "  help         Show this help message"
    echo
    echo "Examples:"
    echo "  $0 dev       # Deploy development environment"
    echo "  $0 prod      # Deploy production environment"
    echo "  $0 logs prod # Show production logs"
    echo "  $0 test      # Run basic tests"
}

# Main script logic
main() {
    case "${1:-help}" in
        "dev")
            check_prerequisites
            setup_storage
            deploy_dev
            ;;
        "prod")
            check_prerequisites
            setup_storage
            deploy_prod
            ;;
        "stop")
            stop_services
            ;;
        "logs")
            show_logs "$2"
            ;;
        "status")
            show_status
            ;;
        "test")
            run_tests
            ;;
        "setup")
            setup_storage
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# Run main function with all arguments
main "$@"

#!/bin/bash

# GFP CoreX Deployment Script
# Usage: ./scripts/deploy.sh [environment]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default environment
ENVIRONMENT=${1:-development}

echo -e "${BLUE}🚀 GFP CoreX Deployment Script${NC}"
echo -e "${BLUE}Environment: ${ENVIRONMENT}${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Create necessary directories
mkdir -p data/pg
mkdir -p data/redis
mkdir -p logs

print_status "Created necessary directories"

# Check if configs directory exists
if [ ! -d "configs" ]; then
    print_error "Configs directory not found. Please ensure you're in the project root."
    exit 1
fi

# Validate configuration files
print_status "Validating configuration files..."
for config_file in configs/*.yaml; do
    if [ -f "$config_file" ]; then
        echo "  - Found: $(basename "$config_file")"
    fi
done

# Build Docker image
print_status "Building Docker image..."
docker build -t gfp-corex .

# Stop existing containers
print_status "Stopping existing containers..."
docker-compose down --remove-orphans

# Start services based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    print_status "Starting production environment..."
    docker-compose --profile production up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be healthy..."
    sleep 30
    
    # Check service health
    if docker-compose ps | grep -q "unhealthy"; then
        print_warning "Some services are unhealthy. Check logs with: docker-compose logs"
    else
        print_status "All services are healthy!"
    fi
    
elif [ "$ENVIRONMENT" = "development" ]; then
    print_status "Starting development environment..."
    docker-compose up -d
    
    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 15
    
else
    print_error "Unknown environment: $ENVIRONMENT"
    print_error "Supported environments: development, production"
    exit 1
fi

# Show service status
print_status "Service status:"
docker-compose ps

# Show available endpoints
print_status "Available endpoints:"
echo "  - Main API: http://localhost:8000"
echo "  - Documentation: http://localhost:8000/docs"
echo "  - Health Check: http://localhost:8000/health"

# Show configuration endpoints
print_status "Configuration endpoints:"
for config_file in configs/*.yaml; do
    if [ -f "$config_file" ]; then
        config_name=$(basename "$config_file" .yaml)
        echo "  - $config_name: http://localhost:8000/api/c/$config_name/api/v1/health"
    fi
done

# Show logs command
print_status "To view logs, run:"
echo "  docker-compose logs -f app"

print_status "Deployment completed successfully! 🎉"


#!/bin/bash

# =====================================================
# ASOUD Platform - Development Environment Setup
# =====================================================

set -e

echo "🚀 Setting up ASOUD Development Environment..."

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

# Check if Docker is running
check_docker() {
    print_status "Checking Docker..."
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop."
        exit 1
    fi
    print_success "Docker is running"
}

# Check if Docker Compose is available
check_docker_compose() {
    print_status "Checking Docker Compose..."
    if ! docker compose version > /dev/null 2>&1; then
        print_error "Docker Compose is not available."
        exit 1
    fi
    print_success "Docker Compose is available"
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    directories=(
        "logs"
        "logs/nginx"
        "logs/django"
        "data/nginx/ssl"
        "data/postgres"
        "data/redis"
        "media"
        "static"
    )
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            print_success "Created directory: $dir"
        fi
    done
}

# Generate self-signed SSL certificates for development
generate_ssl_certs() {
    print_status "Generating self-signed SSL certificates for development..."
    
    if [ ! -f "data/nginx/ssl/dev.crt" ] || [ ! -f "data/nginx/ssl/dev.key" ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout data/nginx/ssl/dev.key \
            -out data/nginx/ssl/dev.crt \
            -subj "/C=IR/ST=Tehran/L=Tehran/O=ASOUD/OU=Development/CN=localhost" \
            -addext "subjectAltName=DNS:localhost,DNS:*.asoud.local,IP:127.0.0.1" 2>/dev/null
        
        print_success "SSL certificates generated"
    else
        print_success "SSL certificates already exist"
    fi
}

# Create .env file if not exists
create_env_file() {
    print_status "Checking .env file..."
    
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            print_success "Created .env file from .env.example"
        else
            print_warning ".env.example not found, creating basic .env file"
            cat > .env << EOF
# ASOUD Development Environment Variables
DJANGO_SECRET_KEY=dev-secret-key-change-in-production-min-50-chars-long
DJANGO_DEBUG=True
DJANGO_SETTINGS_MODULE=config.settings.development

# Database Configuration
DATABASE_NAME=asoud_dev
DATABASE_USERNAME=asoud_user
DATABASE_PASSWORD=asoud_dev_pass

# Redis Configuration
REDIS_PASSWORD=redis_dev_pass

# Development flags
CREATE_SUPERUSER=true
LOAD_SAMPLE_DATA=true
EOF
            print_success "Created basic .env file"
        fi
    else
        print_success ".env file already exists"
    fi
}

# Set proper permissions
set_permissions() {
    print_status "Setting proper permissions..."
    
    # Make sure logs directory is writable
    chmod -R 755 logs/ 2>/dev/null || true
    chmod -R 755 data/ 2>/dev/null || true
    
    print_success "Permissions set"
}

# Pull latest images
pull_images() {
    print_status "Pulling latest Docker images..."
    docker compose -f docker-compose.dev-complete.yaml pull
    print_success "Images pulled successfully"
}

# Build application image
build_app() {
    print_status "Building application image..."
    docker compose -f docker-compose.dev-complete.yaml build web
    print_success "Application image built successfully"
}

# Start services
start_services() {
    print_status "Starting development services..."
    docker compose -f docker-compose.dev-complete.yaml up -d
    print_success "Services started successfully"
}

# Wait for services to be healthy
wait_for_services() {
    print_status "Waiting for services to be healthy..."
    
    services=("db" "redis" "web")
    
    for service in "${services[@]}"; do
        print_status "Waiting for $service to be healthy..."
        timeout=60
        while [ $timeout -gt 0 ]; do
            if docker compose -f docker-compose.dev-complete.yaml ps --format json | jq -r ".[] | select(.Service == \"$service\") | .Health" | grep -q "healthy"; then
                print_success "$service is healthy"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -eq 0 ]; then
            print_warning "$service health check timeout"
        fi
    done
}

# Run database migrations
run_migrations() {
    print_status "Running database migrations..."
    docker compose -f docker-compose.dev-complete.yaml exec web python manage.py migrate
    print_success "Migrations completed"
}

# Create superuser if needed
create_superuser() {
    print_status "Creating superuser..."
    docker compose -f docker-compose.dev-complete.yaml exec web python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(is_superuser=True).exists():
    User.objects.create_superuser('09123456789', password='admin')
    print('Superuser created: 09123456789 / admin')
else:
    print('Superuser already exists')
EOF
    print_success "Superuser setup completed"
}

# Collect static files
collect_static() {
    print_status "Collecting static files..."
    docker compose -f docker-compose.dev-complete.yaml exec web python manage.py collectstatic --noinput
    print_success "Static files collected"
}

# Show service URLs
show_urls() {
    print_success "🎉 Development environment is ready!"
    echo ""
    echo "📍 Service URLs:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🌐 Main Application:      http://localhost"
    echo "🔧 Django Admin:          http://localhost/admin/"
    echo "📊 API Documentation:     http://localhost/api/"
    echo "💾 Database Admin:        http://localhost/adminer/"
    echo "🔴 Redis Commander:       http://localhost/redis/"
    echo "📧 Mail Interface:        http://localhost/mail/"
    echo "📈 Nginx Status:          http://localhost/nginx-status"
    echo ""
    echo "🔐 Development Credentials:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📱 Superuser: 09123456789 / admin"
    echo "🗄️  Database: asoud_dev / asoud_user / asoud_dev_pass"
    echo "🔴 Redis: redis_dev_pass"
    echo ""
    echo "📋 Useful Commands:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔍 View logs:             docker compose -f docker-compose.dev-complete.yaml logs -f"
    echo "🔄 Restart services:      docker compose -f docker-compose.dev-complete.yaml restart"
    echo "🛑 Stop services:         docker compose -f docker-compose.dev-complete.yaml down"
    echo "🗑️  Clean everything:      docker compose -f docker-compose.dev-complete.yaml down -v --remove-orphans"
    echo ""
}

# Main execution
main() {
    echo "🏗️  ASOUD Platform Development Setup"
    echo "====================================="
    
    check_docker
    check_docker_compose
    create_directories
    generate_ssl_certs
    create_env_file
    set_permissions
    pull_images
    build_app
    start_services
    wait_for_services
    run_migrations
    create_superuser
    collect_static
    show_urls
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "start")
        print_status "Starting development environment..."
        docker compose -f docker-compose.dev-complete.yaml up -d
        show_urls
        ;;
    "stop")
        print_status "Stopping development environment..."
        docker compose -f docker-compose.dev-complete.yaml down
        print_success "Development environment stopped"
        ;;
    "restart")
        print_status "Restarting development environment..."
        docker compose -f docker-compose.dev-complete.yaml restart
        print_success "Development environment restarted"
        ;;
    "clean")
        print_warning "This will remove all containers, volumes, and data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            docker compose -f docker-compose.dev-complete.yaml down -v --remove-orphans
            docker system prune -f
            print_success "Development environment cleaned"
        fi
        ;;
    "logs")
        docker compose -f docker-compose.dev-complete.yaml logs -f "${2:-}"
        ;;
    "shell")
        docker compose -f docker-compose.dev-complete.yaml exec web python manage.py shell
        ;;
    "help")
        echo "ASOUD Development Environment Manager"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup     - Full development environment setup (default)"
        echo "  start     - Start all services"
        echo "  stop      - Stop all services"
        echo "  restart   - Restart all services"
        echo "  clean     - Remove all containers and volumes"
        echo "  logs      - Show logs (optionally specify service name)"
        echo "  shell     - Open Django shell"
        echo "  help      - Show this help message"
        ;;
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' for available commands"
        exit 1
        ;;
esac
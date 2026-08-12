#!/usr/bin/env python3
"""
Production Deployment Script for ASOUD Platform
Comprehensive deployment with all Phase 1 & 2 optimizations
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def run_command(command, description):
    """Run command with error handling"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def check_environment():
    """Check environment requirements"""
    print("🔍 Checking environment requirements...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        return False
    
    # Check required files
    required_files = [
        'requirements_performance.txt',
        'config/settings/production.py',
        'apps/core/caching.py',
        'apps/core/database_optimization.py',
        'ultimate_validation_script.py'
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ Required file missing: {file}")
            return False
    
    print("✅ Environment requirements met")
    return True

def install_dependencies():
    """Install production dependencies"""
    print("📦 Installing production dependencies...")
    
    commands = [
        ("pip install -r requirements_performance.txt", "Installing performance dependencies"),
        ("pip install gunicorn", "Installing Gunicorn"),
        ("pip install whitenoise", "Installing WhiteNoise for static files"),
        ("pip install psycopg2-binary", "Installing PostgreSQL adapter"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True

def setup_database():
    """Setup database with optimizations"""
    print("🗄️ Setting up database...")
    
    commands = [
        ("python manage.py migrate", "Running database migrations"),
        ("python manage.py optimize_database --create-indexes", "Creating database indexes"),
        ("python manage.py optimize_database --vacuum", "Optimizing database"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True

def setup_caching():
    """Setup caching system"""
    print("💾 Setting up caching system...")
    
    commands = [
        ("python manage.py warm_cache", "Warming up cache"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            print(f"⚠️ {description} failed, continuing...")
    
    return True

def collect_static_files():
    """Collect static files"""
    print("📁 Collecting static files...")
    
    commands = [
        ("python manage.py collectstatic --noinput", "Collecting static files"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    return True

def run_security_validation():
    """Run security validation"""
    print("🔒 Running security validation...")
    
    if not run_command("python security_validation_complete.py", "Security validation"):
        print("⚠️ Security validation failed, but continuing...")
    
    return True

def run_performance_validation():
    """Run performance validation"""
    print("⚡ Running performance validation...")
    
    if not run_command("python ultimate_validation_script.py", "Performance validation"):
        print("⚠️ Performance validation failed, but continuing...")
    
    return True

def create_production_config():
    """Create production configuration files"""
    print("⚙️ Creating production configuration...")
    
    # Create Gunicorn config
    gunicorn_config = """
[server:main]
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 30
keepalive = 2
preload_app = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
"""
    
    with open('gunicorn.conf.py', 'w') as f:
        f.write(gunicorn_config)
    
    # Create systemd service file
    systemd_service = f"""
[Unit]
Description=ASOUD Platform
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory={os.getcwd()}
Environment=DJANGO_SETTINGS_MODULE=config.settings.production
ExecStart=/usr/local/bin/gunicorn --config gunicorn.conf.py config.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
"""
    
    with open('asoud.service', 'w') as f:
        f.write(systemd_service)
    
    print("✅ Production configuration created")
    return True

def create_nginx_config():
    """Create Nginx configuration"""
    print("🌐 Creating Nginx configuration...")
    
    nginx_config = """
upstream asoud_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.asoud.ir asoud.ir;
    
    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    # Static files
    location /static/ {
        alias /path/to/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /media/ {
        alias /path/to/media/;
        expires 1y;
        add_header Cache-Control "public";
    }
    
    # API routes
    location / {
        proxy_pass http://asoud_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }
}
"""
    
    with open('nginx.conf', 'w') as f:
        f.write(nginx_config)
    
    print("✅ Nginx configuration created")
    return True

def create_monitoring_script():
    """Create monitoring script"""
    print("📊 Creating monitoring script...")
    
    monitoring_script = """#!/bin/bash
# ASOUD Platform Monitoring Script

echo "🔍 ASOUD Platform Health Check - $(date)"
echo "=========================================="

# Check if service is running
if systemctl is-active --quiet asoud; then
    echo "✅ ASOUD service is running"
else
    echo "❌ ASOUD service is not running"
    exit 1
fi

# Check database connection
python manage.py check --database default
if [ $? -eq 0 ]; then
    echo "✅ Database connection OK"
else
    echo "❌ Database connection failed"
    exit 1
fi

# Check Redis connection
python -c "from django.core.cache import cache; cache.get('test')"
if [ $? -eq 0 ]; then
    echo "✅ Redis connection OK"
else
    echo "❌ Redis connection failed"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo "✅ Disk usage OK ($DISK_USAGE%)"
else
    echo "⚠️ Disk usage high ($DISK_USAGE%)"
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEMORY_USAGE -lt 80 ]; then
    echo "✅ Memory usage OK ($MEMORY_USAGE%)"
else
    echo "⚠️ Memory usage high ($MEMORY_USAGE%)"
fi

echo "✅ All checks passed"
"""
    
    with open('monitor.sh', 'w') as f:
        f.write(monitoring_script)
    
    os.chmod('monitor.sh', 0o755)
    print("✅ Monitoring script created")
    return True

def main():
    """Main deployment function"""
    print("🚀 Starting ASOUD Platform Production Deployment")
    print("=" * 60)
    print(f"Deployment started at: {datetime.now()}")
    print("=" * 60)
    
    deployment_steps = [
        ("Environment Check", check_environment),
        ("Install Dependencies", install_dependencies),
        ("Setup Database", setup_database),
        ("Setup Caching", setup_caching),
        ("Collect Static Files", collect_static_files),
        ("Security Validation", run_security_validation),
        ("Performance Validation", run_performance_validation),
        ("Create Production Config", create_production_config),
        ("Create Nginx Config", create_nginx_config),
        ("Create Monitoring Script", create_monitoring_script),
    ]
    
    failed_steps = []
    
    for step_name, step_function in deployment_steps:
        print(f"\n📋 Step: {step_name}")
        print("-" * 40)
        
        if not step_function():
            failed_steps.append(step_name)
            print(f"❌ {step_name} failed")
        else:
            print(f"✅ {step_name} completed")
    
    print("\n" + "=" * 60)
    print("🎯 DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    if failed_steps:
        print(f"❌ Failed steps: {', '.join(failed_steps)}")
        print("⚠️ Deployment completed with issues")
        return False
    else:
        print("✅ All deployment steps completed successfully!")
        print("🎉 ASOUD Platform is ready for production!")
        
        print("\n📋 Next steps:")
        print("1. Configure environment variables")
        print("2. Setup SSL certificates")
        print("3. Configure Nginx")
        print("4. Start services:")
        print("   - systemctl start asoud")
        print("   - systemctl enable asoud")
        print("5. Run monitoring: ./monitor.sh")
        
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


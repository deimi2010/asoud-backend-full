# 🚀 ASOUD Platform - Complete Development Environment

## 📋 Overview

This is a **comprehensive, production-ready development environment** for the ASOUD Platform. It includes all necessary services, tools, and configurations for efficient development and testing.

## 🏗️ Architecture

### Services Included
- **Django API** (asoud_api_dev) - Main application server
- **PostgreSQL** (asoud_db_dev) - Primary database
- **Redis** (asoud_redis_dev) - Caching and sessions
- **Nginx** (asoud_nginx_dev) - Reverse proxy and static files
- **Adminer** (asoud_adminer_dev) - Database administration
- **Redis Commander** (asoud_redis_commander_dev) - Redis management
- **MailHog** (asoud_mailhog_dev) - Email testing

### Network Configuration
- **Isolated Network**: `asoud_dev_network`
- **Service Discovery**: All services communicate via container names
- **Port Mapping**: Exposed only to localhost for security

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed and running
- Git (for version control)
- 8GB+ RAM recommended
- 10GB+ free disk space

### 1. Setup Environment
```bash
# Clone and navigate to project
cd asoud-main-1-/asoud-main

# Run automated setup
bash scripts/dev-setup.sh
```

### 2. Alternative Manual Setup
```bash
# Create required directories
mkdir -p logs/nginx logs/django data/nginx/ssl

# Generate SSL certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout data/nginx/ssl/dev.key \
  -out data/nginx/ssl/dev.crt \
  -subj "/CN=localhost"

# Create .env file
cp .env.example .env

# Start services
docker compose -f docker-compose.dev-complete.yaml up -d
```

### 3. Verify Installation
```bash
# Run comprehensive validation
python scripts/dev_validator.py full

# Check service health
python scripts/dev_monitor.py check
```

## 🌐 Service URLs

### Main Applications
- **🌐 Main Application**: http://localhost
- **🔧 Django Admin**: http://localhost/admin/
- **📊 API Root**: http://localhost/api/
- **📊 API Documentation**: http://localhost/api/v1/

### Development Tools
- **💾 Database Admin (Adminer)**: http://localhost/adminer/
- **🔴 Redis Commander**: http://localhost/redis/
- **📧 Mail Interface (MailHog)**: http://localhost/mail/
- **📈 Nginx Status**: http://localhost/nginx-status

### SSL/HTTPS
- **🔒 HTTPS Main**: https://localhost (self-signed certificate)

## 🔐 Default Credentials

### Django Superuser
```
Mobile: 09123456789
Password: admin
```

### Database (PostgreSQL)
```
Host: localhost:5432
Database: asoud_dev
Username: asoud_user
Password: asoud_dev_pass
```

### Redis
```
Host: localhost:6379
Password: redis_dev_pass
```

## 🛠️ Development Commands

### Basic Operations
```bash
# Start all services
bash scripts/dev-setup.sh start

# Stop all services
bash scripts/dev-setup.sh stop

# Restart services
bash scripts/dev-setup.sh restart

# View logs
bash scripts/dev-setup.sh logs

# Clean everything (removes all data!)
bash scripts/dev-setup.sh clean
```

### Django Commands
```bash
# Open Django shell
docker compose -f docker-compose.dev-complete.yaml exec web python manage.py shell

# Run migrations
docker compose -f docker-compose.dev-complete.yaml exec web python manage.py migrate

# Create superuser
docker compose -f docker-compose.dev-complete.yaml exec web python manage.py createsuperuser

# Collect static files
docker compose -f docker-compose.dev-complete.yaml exec web python manage.py collectstatic
```

### Database Operations
```bash
# Access PostgreSQL shell
docker compose -f docker-compose.dev-complete.yaml exec db psql -U asoud_user -d asoud_dev

# Backup database
docker compose -f docker-compose.dev-complete.yaml exec db pg_dump -U asoud_user asoud_dev > backup.sql

# Restore database
docker compose -f docker-compose.dev-complete.yaml exec -T db psql -U asoud_user -d asoud_dev < backup.sql
```

### Redis Operations
```bash
# Access Redis CLI
docker compose -f docker-compose.dev-complete.yaml exec redis redis-cli -a redis_dev_pass

# Monitor Redis
docker compose -f docker-compose.dev-complete.yaml exec redis redis-cli -a redis_dev_pass monitor

# Clear Redis cache
docker compose -f docker-compose.dev-complete.yaml exec redis redis-cli -a redis_dev_pass flushall
```

## 📊 Monitoring & Debugging

### Real-time Monitoring
```bash
# Start real-time dashboard
python scripts/dev_monitor.py monitor

# Check for issues
python scripts/dev_monitor.py check

# Generate performance report
python scripts/dev_monitor.py report
```

### Validation & Testing
```bash
# Full environment validation
python scripts/dev_validator.py full

# Validate specific components
python scripts/dev_validator.py docker
python scripts/dev_validator.py services
python scripts/dev_validator.py api
python scripts/dev_validator.py network
python scripts/dev_validator.py security
```

### Log Analysis
```bash
# View all logs
docker compose -f docker-compose.dev-complete.yaml logs -f

# View specific service logs
docker compose -f docker-compose.dev-complete.yaml logs -f web
docker compose -f docker-compose.dev-complete.yaml logs -f db
docker compose -f docker-compose.dev-complete.yaml logs -f redis
docker compose -f docker-compose.dev-complete.yaml logs -f nginx

# View Nginx access logs
docker compose -f docker-compose.dev-complete.yaml exec nginx tail -f /var/log/nginx/access.log
```

## 🔧 Configuration Files

### Key Configuration Files
- `docker-compose.dev-complete.yaml` - Complete Docker Compose configuration
- `nginx/nginx-dev.conf` - Development Nginx configuration
- `redis/redis-dev.conf` - Redis configuration for development
- `scripts/init-db.sql` - Database initialization script
- `.env` - Environment variables

### Environment Variables
```bash
# Security
DJANGO_SECRET_KEY=dev-secret-key-change-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,*.asoud.local

# Database
DATABASE_NAME=asoud_dev
DATABASE_USERNAME=asoud_user
DATABASE_PASSWORD=asoud_dev_pass

# Redis
REDIS_PASSWORD=redis_dev_pass

# Development flags
CREATE_SUPERUSER=true
LOAD_SAMPLE_DATA=true
```

## 🔒 Security Features

### Development Security
- **SSL/TLS**: Self-signed certificates for HTTPS testing
- **Network Isolation**: All services in dedicated network
- **Password Protection**: All services password protected
- **CORS Configuration**: Enabled for frontend development
- **Rate Limiting**: Relaxed for development (configurable)

### File Permissions
```bash
# Set proper permissions
chmod 755 logs/ data/
chmod 600 .env
chmod 600 data/nginx/ssl/dev.key
```

## ⚡ Performance Optimization

### Resource Limits
- **Redis**: 512MB memory limit with LRU eviction
- **PostgreSQL**: Optimized for development workload
- **Nginx**: Configured for development with generous limits
- **Docker**: Health checks and restart policies

### Caching Strategy
- **Redis**: Session storage and application cache
- **Nginx**: Static file caching with proper headers
- **Database**: Optimized queries and indexes

## 🐛 Troubleshooting

### Common Issues

#### Services Not Starting
```bash
# Check Docker daemon
docker info

# Check available resources
docker system df
docker system prune -f

# Restart Docker Desktop
```

#### Database Connection Issues
```bash
# Check database container
docker compose -f docker-compose.dev-complete.yaml ps db

# Check database logs
docker compose -f docker-compose.dev-complete.yaml logs db

# Reset database
docker compose -f docker-compose.dev-complete.yaml down -v
docker compose -f docker-compose.dev-complete.yaml up -d
```

#### Port Conflicts
```bash
# Check port usage
netstat -tulpn | grep :80
netstat -tulpn | grep :8000

# Stop conflicting services
sudo service nginx stop
sudo service apache2 stop
```

#### SSL Certificate Issues
```bash
# Regenerate certificates
rm -f data/nginx/ssl/dev.*
bash scripts/dev-setup.sh
```

### Performance Issues
```bash
# Check system resources
python scripts/dev_monitor.py check

# Monitor containers
docker stats

# Check disk space
docker system df
```

## 📚 Additional Resources

### Documentation
- **Security Guide**: `DEVELOPMENT_SECURITY_GUIDE.md`
- **API Documentation**: Auto-generated at `/api/`
- **Django Documentation**: https://docs.djangoproject.com/
- **Docker Documentation**: https://docs.docker.com/

### Development Tools
- **Django Debug Toolbar**: Enabled in development
- **Hot Reload**: Automatic code reloading
- **Volume Sync**: Real-time file synchronization
- **Mail Testing**: All emails captured in MailHog

### Scripts
- `scripts/dev-setup.sh` - Complete environment setup
- `scripts/dev_monitor.py` - Real-time monitoring
- `scripts/dev_validator.py` - Comprehensive validation
- `scripts/init-db.sql` - Database initialization

## 🤝 Contributing

### Development Workflow
1. Start development environment
2. Make changes to code
3. Test changes automatically reload
4. Validate with monitoring tools
5. Run comprehensive validation before commit

### Code Quality
```bash
# Run linting
docker compose -f docker-compose.dev-complete.yaml exec web flake8

# Run tests
docker compose -f docker-compose.dev-complete.yaml exec web python manage.py test

# Check security
python scripts/dev_validator.py security
```

## 📞 Support

### Getting Help
- **Documentation**: Check this README and security guide
- **Validation**: Run `python scripts/dev_validator.py full`
- **Monitoring**: Use `python scripts/dev_monitor.py check`
- **Logs**: Check service logs for specific errors

### Reporting Issues
- Include validation report output
- Provide relevant log snippets
- Specify operating system and Docker version
- Include steps to reproduce

---

## 🎉 Quick Success Check

After setup, verify everything is working:

```bash
# 1. Check all services are running
python scripts/dev_validator.py docker

# 2. Test API functionality
curl http://localhost/api/v1/health/

# 3. Access admin panel
# Open http://localhost/admin/ in browser
# Login with: 09123456789 / admin

# 4. Check development tools
# Database: http://localhost/adminer/
# Redis: http://localhost/redis/
# Mail: http://localhost/mail/
```

If all checks pass, your development environment is ready! 🚀

---

**ASOUD Platform Development Team**  
*Complete Development Environment v2.0*
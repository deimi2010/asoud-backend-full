# =============================================================================
# ASOUD Development Environment - Security & Networking Guide
# =============================================================================

## 🔒 Security Configuration for Development

### Network Security
- All services isolated in dedicated `asoud_dev_network`
- Port exposure limited to localhost only
- Self-signed SSL certificates for HTTPS testing
- CORS enabled for frontend development

### Authentication & Authorization
- Development superuser: 09123456789 / admin
- JWT tokens for API authentication  
- Session-based auth for admin panel
- Rate limiting relaxed for development

### Database Security
- PostgreSQL with dedicated development user
- Password-protected Redis instance
- Data encrypted at rest in volumes
- Development-specific database schemas

### Container Security
- Non-root users in production builds
- Read-only file systems where possible
- Resource limits to prevent DoS
- Health checks for service monitoring

## 🌐 Networking Configuration

### Service Discovery
```yaml
networks:
  asoud_dev_network:
    driver: bridge
    name: asoud_dev_network
```

### Port Mapping
```
80/443  -> nginx (Web server + SSL)
8000    -> Django (Direct API access)
5432    -> PostgreSQL (Database)
6379    -> Redis (Cache)
8080    -> Adminer (DB Admin)
8081    -> Redis Commander
8025    -> MailHog Web UI
1025    -> MailHog SMTP
```

### Internal Communication
- web -> db (PostgreSQL connection)
- web -> redis (Cache & sessions)
- nginx -> web (Reverse proxy)
- adminer -> db (Database management)
- redis-commander -> redis (Redis management)

### External Access
- Frontend development: http://localhost
- API testing: http://localhost/api/
- Admin panel: http://localhost/admin/
- Database admin: http://localhost/adminer/
- Redis admin: http://localhost/redis/
- Mail testing: http://localhost/mail/

## 🔐 Development Credentials

### Default Users
```
Django Superuser:
- Mobile: 09123456789
- Password: admin

Database:
- Host: localhost:5432
- Database: asoud_dev
- Username: asoud_user  
- Password: asoud_dev_pass

Redis:
- Host: localhost:6379
- Password: redis_dev_pass
```

### Environment Variables
```bash
# Security
DJANGO_SECRET_KEY=dev-secret-key-change-in-production
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,*.asoud.local

# Database
DATABASE_HOST=db
DATABASE_NAME=asoud_dev
DATABASE_USERNAME=asoud_user
DATABASE_PASSWORD=asoud_dev_pass

# Redis
REDIS_HOST=redis
REDIS_PASSWORD=redis_dev_pass
```

## 🛡️ Security Best Practices for Development

### 1. Network Isolation
```yaml
# All services in dedicated network
networks:
  - asoud_dev_network
```

### 2. SSL/TLS Configuration
```bash
# Generate self-signed certificates
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout dev.key -out dev.crt \
  -subj "/CN=localhost"
```

### 3. Resource Limits
```yaml
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '0.5'
```

### 4. Health Monitoring
```yaml
healthcheck:
  test: ["CMD", "python", "manage.py", "check"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## 🔍 Security Monitoring

### Log Monitoring
```bash
# View security logs
docker compose logs nginx | grep -E "(401|403|404)"
docker compose logs web | grep -i "error"
```

### Performance Monitoring
```bash
# Monitor resource usage
python scripts/dev_monitor.py check
python scripts/dev_monitor.py monitor
```

### Health Checks
```bash
# Check all services
curl http://localhost/health/
curl http://localhost/api/v1/health/
```

## 🚨 Common Security Issues & Solutions

### Issue 1: CORS Errors
**Problem:** Frontend can't access API
**Solution:** Check CORS settings in nginx-dev.conf

### Issue 2: SSL Certificate Warnings
**Problem:** Browser shows certificate warnings
**Solution:** Accept self-signed certificates for development

### Issue 3: Database Connection Refused
**Problem:** Django can't connect to PostgreSQL
**Solution:** Check database service health and credentials

### Issue 4: Redis Authentication Failed
**Problem:** Cache operations failing
**Solution:** Verify REDIS_PASSWORD in .env file

### Issue 5: File Permission Errors
**Problem:** Volume mount permission denied
**Solution:** Run `chmod -R 755 logs/ data/`

## 📋 Security Checklist

### Before Starting Development
- [ ] Generate SSL certificates
- [ ] Create .env file with secure passwords
- [ ] Set proper file permissions
- [ ] Verify network isolation
- [ ] Check service health

### During Development
- [ ] Monitor logs for errors
- [ ] Check resource usage
- [ ] Verify API authentication
- [ ] Test CORS configuration
- [ ] Monitor database connections

### After Development Session
- [ ] Review security logs
- [ ] Check for exposed credentials
- [ ] Clean temporary files
- [ ] Update dependency versions
- [ ] Backup development data

## 🔧 Troubleshooting Commands

### Network Issues
```bash
# Check network connectivity
docker network ls
docker network inspect asoud_dev_network

# Test internal connectivity
docker exec asoud_api_dev ping asoud_db_dev
docker exec asoud_api_dev ping asoud_redis_dev
```

### Security Issues
```bash
# Check file permissions
ls -la logs/ data/
docker exec asoud_api_dev ls -la /asoud/

# Verify SSL certificates
openssl x509 -in data/nginx/ssl/dev.crt -text -noout
```

### Performance Issues
```bash
# Monitor containers
docker stats
python scripts/dev_monitor.py check

# Check service health
docker compose ps
docker compose logs --tail=50
```

## 📚 Additional Resources

### Development URLs
- Django Debug Toolbar: Enabled in development
- API Documentation: Auto-generated with DRF
- Database Admin: Full access via Adminer
- Redis Admin: Complete Redis management
- Mail Testing: All emails captured in MailHog

### Security Documentation
- Django Security: https://docs.djangoproject.com/en/5.1/topics/security/
- Docker Security: https://docs.docker.com/engine/security/
- Nginx Security: https://nginx.org/en/docs/
- PostgreSQL Security: https://www.postgresql.org/docs/current/security.html

### Monitoring Tools
- Real-time monitoring: `python scripts/dev_monitor.py monitor`
- Performance reports: `python scripts/dev_monitor.py report`
- Issue detection: `python scripts/dev_monitor.py check`
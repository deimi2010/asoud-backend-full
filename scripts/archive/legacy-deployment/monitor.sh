#!/bin/bash
# ASOUD Platform Monitoring Script

echo "🔍 ASOUD Platform Health Check - $(date)"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if service is running
if systemctl is-active --quiet asoud; then
    echo -e "${GREEN}✅ ASOUD service is running${NC}"
else
    echo -e "${RED}❌ ASOUD service is not running${NC}"
    exit 1
fi

# Check database connection
python3 manage.py check --database default
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Database connection OK${NC}"
else
    echo -e "${RED}❌ Database connection failed${NC}"
    exit 1
fi

# Check Redis connection
python3 -c "from django.core.cache import cache; cache.get('test')"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Redis connection OK${NC}"
else
    echo -e "${RED}❌ Redis connection failed${NC}"
    exit 1
fi

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -lt 80 ]; then
    echo -e "${GREEN}✅ Disk usage OK ($DISK_USAGE%)${NC}"
else
    echo -e "${YELLOW}⚠️ Disk usage high ($DISK_USAGE%)${NC}"
fi

# Check memory usage
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEMORY_USAGE -lt 80 ]; then
    echo -e "${GREEN}✅ Memory usage OK ($MEMORY_USAGE%)${NC}"
else
    echo -e "${YELLOW}⚠️ Memory usage high ($MEMORY_USAGE%)${NC}"
fi

# Check CPU usage
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | awk -F'%' '{print $1}')
if [ $(echo "$CPU_USAGE < 80" | bc) -eq 1 ]; then
    echo -e "${GREEN}✅ CPU usage OK ($CPU_USAGE%)${NC}"
else
    echo -e "${YELLOW}⚠️ CPU usage high ($CPU_USAGE%)${NC}"
fi

# Check load average
LOAD_AVG=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
if [ $(echo "$LOAD_AVG < 4" | bc) -eq 1 ]; then
    echo -e "${GREEN}✅ Load average OK ($LOAD_AVG)${NC}"
else
    echo -e "${YELLOW}⚠️ Load average high ($LOAD_AVG)${NC}"
fi

# Check network connectivity
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Network connectivity OK${NC}"
else
    echo -e "${RED}❌ Network connectivity failed${NC}"
fi

# Check SSL certificate (if applicable)
if [ -f "/etc/ssl/certs/asoud.crt" ]; then
    SSL_EXPIRY=$(openssl x509 -enddate -noout -in /etc/ssl/certs/asoud.crt | cut -d= -f2)
    SSL_EXPIRY_EPOCH=$(date -d "$SSL_EXPIRY" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( (SSL_EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
    
    if [ $DAYS_UNTIL_EXPIRY -gt 30 ]; then
        echo -e "${GREEN}✅ SSL certificate OK (expires in $DAYS_UNTIL_EXPIRY days)${NC}"
    elif [ $DAYS_UNTIL_EXPIRY -gt 7 ]; then
        echo -e "${YELLOW}⚠️ SSL certificate expires soon ($DAYS_UNTIL_EXPIRY days)${NC}"
    else
        echo -e "${RED}❌ SSL certificate expires very soon ($DAYS_UNTIL_EXPIRY days)${NC}"
    fi
fi

# Check log files
if [ -f "/var/log/nginx/asoud_error.log" ]; then
    ERROR_COUNT=$(grep -c "error" /var/log/nginx/asoud_error.log | tail -1)
    if [ $ERROR_COUNT -lt 10 ]; then
        echo -e "${GREEN}✅ Nginx error log OK ($ERROR_COUNT errors)${NC}"
    else
        echo -e "${YELLOW}⚠️ Nginx error log has many errors ($ERROR_COUNT)${NC}"
    fi
fi

# Check application logs
if [ -f "/var/log/asoud/app.log" ]; then
    APP_ERROR_COUNT=$(grep -c "ERROR" /var/log/asoud/app.log | tail -1)
    if [ $APP_ERROR_COUNT -lt 5 ]; then
        echo -e "${GREEN}✅ Application log OK ($APP_ERROR_COUNT errors)${NC}"
    else
        echo -e "${YELLOW}⚠️ Application log has many errors ($APP_ERROR_COUNT)${NC}"
    fi
fi

# Check if all critical services are running
SERVICES=("postgresql" "redis" "nginx" "asoud")
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet $service; then
        echo -e "${GREEN}✅ $service service is running${NC}"
    else
        echo -e "${RED}❌ $service service is not running${NC}"
    fi
done

# Performance metrics
echo ""
echo "📊 Performance Metrics:"
echo "----------------------"

# Database connections
DB_CONNECTIONS=$(psql -U postgres -d asoud -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | tail -n +3 | head -n 1 | tr -d ' ')
if [ ! -z "$DB_CONNECTIONS" ]; then
    echo "Database connections: $DB_CONNECTIONS"
fi

# Redis memory usage
REDIS_MEMORY=$(redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
if [ ! -z "$REDIS_MEMORY" ]; then
    echo "Redis memory usage: $REDIS_MEMORY"
fi

# Active users (if available)
ACTIVE_USERS=$(ps aux | grep -c gunicorn)
echo "Active worker processes: $ACTIVE_USERS"

echo ""
echo -e "${GREEN}✅ All critical checks passed${NC}"
echo "=========================================="


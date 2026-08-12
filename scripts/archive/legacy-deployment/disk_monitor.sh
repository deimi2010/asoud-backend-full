#!/bin/bash

# Disk Space Monitoring Script
# Created for Asoud Project

# Configuration
THRESHOLD_WARNING=85
THRESHOLD_CRITICAL=95
LOG_FILE="/var/log/disk_monitor.log"
ALERT_EMAIL="admin@asoud.ir"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to check disk usage
check_disk_usage() {
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    local available=$(df / | awk 'NR==2 {print $4}')
    
    echo "=== Disk Usage Report ==="
    echo "Current Usage: ${usage}%"
    echo "Available Space: ${available}"
    
    if [ "$usage" -ge "$THRESHOLD_CRITICAL" ]; then
        echo -e "${RED}CRITICAL: Disk usage is ${usage}%${NC}"
        log_message "CRITICAL: Disk usage is ${usage}%"
        
        # Emergency cleanup
        echo "Performing emergency cleanup..."
        docker system prune -f
        sudo apt clean 2>/dev/null || true
        
        # Check again after cleanup
        local new_usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
        echo "After cleanup: ${new_usage}%"
        log_message "After emergency cleanup: ${new_usage}%"
        
    elif [ "$usage" -ge "$THRESHOLD_WARNING" ]; then
        echo -e "${YELLOW}WARNING: Disk usage is ${usage}%${NC}"
        log_message "WARNING: Disk usage is ${usage}%"
        
        # Gentle cleanup
        echo "Performing gentle cleanup..."
        docker volume prune -f
        docker builder prune -f
        
    else
        echo -e "${GREEN}OK: Disk usage is ${usage}%${NC}"
        log_message "OK: Disk usage is ${usage}%"
    fi
}

# Function to check Docker system
check_docker_system() {
    echo -e "\n=== Docker System Status ==="
    docker system df
    
    # Check for large containers
    echo -e "\n=== Container Sizes ==="
    docker ps --format "table {{.Names}}\t{{.Size}}"
}

# Function to suggest cleanup actions
suggest_cleanup() {
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [ "$usage" -ge "$THRESHOLD_WARNING" ]; then
        echo -e "\n=== Cleanup Suggestions ==="
        echo "1. Remove unused Docker volumes: docker volume prune -f"
        echo "2. Remove unused Docker images: docker image prune -f"
        echo "3. Clean build cache: docker builder prune -f"
        echo "4. Clean system packages: sudo apt autoremove -y"
        echo "5. Clean logs: sudo journalctl --vacuum-time=7d"
    fi
}

# Main execution
main() {
    echo "Starting disk monitoring check..."
    log_message "Disk monitoring check started"
    
    check_disk_usage
    check_docker_system
    suggest_cleanup
    
    echo -e "\n=== Monitoring Complete ==="
    log_message "Disk monitoring check completed"
}

# Run main function
main "$@"



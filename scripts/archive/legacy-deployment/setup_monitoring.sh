#!/bin/bash

# Setup Monitoring Script for Asoud Project
# This script sets up automated disk monitoring

echo "=== Setting up Disk Monitoring ==="

# Create log directory
sudo mkdir -p /var/log/asoud
sudo chown $USER:$USER /var/log/asoud

# Update disk monitor script to use local log
sed -i 's|/var/log/disk_monitor.log|/var/log/asoud/disk_monitor.log|g' scripts/disk_monitor.sh

# Create cron job
echo "Setting up cron job for disk monitoring..."
(crontab -l 2>/dev/null; echo "*/30 * * * * $(pwd)/scripts/disk_monitor.sh") | crontab -

# Create log rotation
sudo tee /etc/logrotate.d/asoud-monitoring > /dev/null <<EOF
/var/log/asoud/disk_monitor.log {
    daily
    missingok
    rotate 7
    compress
    notifempty
    create 644 $USER $USER
}
EOF

echo "=== Monitoring Setup Complete ==="
echo "Disk monitoring will run every 30 minutes"
echo "Logs will be rotated daily and kept for 7 days"
echo "Log file: /var/log/asoud/disk_monitor.log"



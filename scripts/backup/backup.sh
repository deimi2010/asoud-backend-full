#!/bin/bash
# =============================================================================
# PostgreSQL Automated Backup Script
# Creates timestamped backups with retention policy
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/asoud_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Database connection
PGHOST="${DATABASE_HOST:-postgres}"
PGPORT="${DATABASE_PORT:-5432}"
PGDATABASE="${POSTGRES_DB}"
PGUSER="${POSTGRES_USER}"

echo -e "${GREEN}[INFO]${NC} Starting PostgreSQL backup..."
echo -e "${GREEN}[INFO]${NC} Database: ${PGDATABASE}"
echo -e "${GREEN}[INFO]${NC} Timestamp: ${TIMESTAMP}"

# Create backup directory if not exists
mkdir -p "${BACKUP_DIR}"

# Create backup
echo -e "${YELLOW}[BACKUP]${NC} Creating compressed database dump..."
pg_dump -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${PGDATABASE}" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    2>&1 | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    echo -e "${GREEN}[SUCCESS]${NC} Backup created successfully!"
    echo -e "${GREEN}[INFO]${NC} Backup file: ${BACKUP_FILE}"
    echo -e "${GREEN}[INFO]${NC} Backup size: ${BACKUP_SIZE}"
else
    echo -e "${RED}[ERROR]${NC} Backup failed!"
    exit 1
fi

# Cleanup old backups
echo -e "${YELLOW}[CLEANUP]${NC} Removing backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "asoud_backup_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
REMAINING_BACKUPS=$(find "${BACKUP_DIR}" -name "asoud_backup_*.sql.gz" | wc -l)
echo -e "${GREEN}[INFO]${NC} Remaining backups: ${REMAINING_BACKUPS}"

# Test backup integrity
echo -e "${YELLOW}[TEST]${NC} Testing backup integrity..."
if gunzip -t "${BACKUP_FILE}" 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Backup integrity verified!"
else
    echo -e "${RED}[ERROR]${NC} Backup file is corrupted!"
    exit 1
fi

echo -e "${GREEN}[COMPLETE]${NC} Backup process completed successfully!"
exit 0

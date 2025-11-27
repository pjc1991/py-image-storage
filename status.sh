#!/bin/bash

#################################################################################
# Image Storage Service - Status Script
#
# This script checks the status of the image storage service.
#################################################################################

# Configuration
SERVICE_NAME="Image Storage Service"
PID_FILE="service.pid"
LOG_FILE="logs/service.log"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_status() {
    echo -e "$1"
}

get_process_info() {
    local pid=$1
    ps -p "$pid" -o pid,ppid,user,%cpu,%mem,etime,cmd --no-headers 2>/dev/null
}

# Header
echo ""
echo "========================================"
echo "  ${SERVICE_NAME}"
echo "  Status Check"
echo "========================================"
echo ""

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    print_status "${RED}✗ Status: NOT RUNNING${NC}"
    print_status "  PID file not found: $PID_FILE"

    # Try to find process by name
    PROCESS=$(ps aux | grep "python.*main.py" | grep -v "grep" | awk '{print $2}')
    if [ -n "$PROCESS" ]; then
        print_status "${YELLOW}⚠ Warning: Found orphan process${NC}"
        print_status "  PID: $PROCESS"
        print_status "  This process may be running without PID file."
    fi

    echo ""
    print_status "To start the service:"
    print_status "  ${BLUE}./start.sh${NC}"
    echo ""
    exit 1
fi

# Read PID
PID=$(cat "$PID_FILE")

# Check if process is running
if ! ps -p "$PID" > /dev/null 2>&1; then
    print_status "${RED}✗ Status: NOT RUNNING${NC}"
    print_status "  PID file exists but process is dead"
    print_status "  PID: $PID (from file)"
    print_status "  PID file: $PID_FILE"
    echo ""
    print_status "${YELLOW}⚠ Cleaning up stale PID file...${NC}"
    rm -f "$PID_FILE"
    echo ""
    print_status "To start the service:"
    print_status "  ${BLUE}./start.sh${NC}"
    echo ""
    exit 1
fi

# Service is running
print_status "${GREEN}✓ Status: RUNNING${NC}"
echo ""

# Process information
print_status "${BLUE}Process Information:${NC}"
PROCESS_INFO=$(get_process_info "$PID")
if [ -n "$PROCESS_INFO" ]; then
    echo "  PID      : $(echo "$PROCESS_INFO" | awk '{print $1}')"
    echo "  PPID     : $(echo "$PROCESS_INFO" | awk '{print $2}')"
    echo "  User     : $(echo "$PROCESS_INFO" | awk '{print $3}')"
    echo "  CPU%     : $(echo "$PROCESS_INFO" | awk '{print $4}')"
    echo "  Memory%  : $(echo "$PROCESS_INFO" | awk '{print $5}')"
    echo "  Uptime   : $(echo "$PROCESS_INFO" | awk '{print $6}')"
    echo "  Command  : $(echo "$PROCESS_INFO" | awk '{for(i=7;i<=NF;i++) printf "%s ", $i; print ""}')"
else
    echo "  PID: $PID"
fi
echo ""

# Log file information
print_status "${BLUE}Log Information:${NC}"
if [ -f "$LOG_FILE" ]; then
    LOG_SIZE=$(du -h "$LOG_FILE" | cut -f1)
    LOG_LINES=$(wc -l < "$LOG_FILE")
    LAST_MODIFIED=$(stat -c '%y' "$LOG_FILE" 2>/dev/null || stat -f '%Sm' "$LOG_FILE" 2>/dev/null)

    echo "  Log file : $LOG_FILE"
    echo "  Size     : $LOG_SIZE"
    echo "  Lines    : $LOG_LINES"
    if [ -n "$LAST_MODIFIED" ]; then
        echo "  Modified : $LAST_MODIFIED"
    fi

    echo ""
    print_status "${BLUE}Recent Activity (last 5 lines):${NC}"
    echo "  ----------------------------------------"
    tail -n 5 "$LOG_FILE" | sed 's/^/  /'
    echo "  ----------------------------------------"
else
    echo "  ${YELLOW}Log file not found: $LOG_FILE${NC}"
fi
echo ""

# Available commands
print_status "${BLUE}Available Commands:${NC}"
print_status "  ${GREEN}./stop.sh${NC}          - Stop the service"
print_status "  ${GREEN}./restart.sh${NC}       - Restart the service"
print_status "  ${GREEN}./watch_logs.sh${NC}    - Watch logs in real-time"
print_status "  ${GREEN}./watch_logs.sh ERROR${NC} - Watch only errors"
echo ""

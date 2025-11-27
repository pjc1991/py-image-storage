#!/bin/bash

#################################################################################
# Image Storage Service - Stop Script
#
# This script gracefully stops the image storage service.
# It sends SIGTERM first for graceful shutdown, then SIGKILL if needed.
#################################################################################

# Configuration
SERVICE_NAME="Image Storage Service"
PID_FILE="service.pid"
GRACEFUL_TIMEOUT=30  # Seconds to wait for graceful shutdown

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Main script
print_info "Stopping ${SERVICE_NAME}..."

# Check if PID file exists
if [ ! -f "$PID_FILE" ]; then
    print_error "PID file not found: $PID_FILE"
    print_info "Service may not be running, or was started manually."

    # Try to find process by name
    print_info "Searching for process by name..."
    PROCESS=$(ps aux | grep "python.*main.py" | grep -v "grep" | awk '{print $2}')

    if [ -z "$PROCESS" ]; then
        print_error "No running process found"
        exit 1
    else
        print_warning "Found process: $PROCESS"
        PID=$PROCESS
    fi
else
    PID=$(cat "$PID_FILE")
fi

# Check if process is actually running
if ! ps -p "$PID" > /dev/null 2>&1; then
    print_error "Process $PID is not running"
    print_info "Cleaning up PID file..."
    rm -f "$PID_FILE"
    exit 1
fi

print_info "Found running process (PID: $PID)"

# Send SIGTERM for graceful shutdown
print_info "Sending SIGTERM for graceful shutdown..."
kill -TERM "$PID" 2>/dev/null

# Wait for graceful shutdown
print_info "Waiting up to ${GRACEFUL_TIMEOUT}s for graceful shutdown..."
for i in $(seq 1 $GRACEFUL_TIMEOUT); do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_info "${GREEN}✓${NC} Service stopped gracefully"
        rm -f "$PID_FILE"
        exit 0
    fi

    # Print progress
    if [ $((i % 5)) -eq 0 ]; then
        echo -n "."
    fi

    sleep 1
done

echo ""  # New line after dots

# If still running, force kill
print_warning "Graceful shutdown timeout. Sending SIGKILL..."
kill -9 "$PID" 2>/dev/null

# Wait a bit more
sleep 2

# Final check
if ps -p "$PID" > /dev/null 2>&1; then
    print_error "Failed to stop process $PID"
    exit 1
else
    print_info "${GREEN}✓${NC} Service forcefully stopped"
    rm -f "$PID_FILE"
    exit 0
fi

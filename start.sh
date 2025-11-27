#!/bin/bash

#################################################################################
# Image Storage Service - Start Script
#
# This script starts the image storage service in the background.
# Logs are written to logs/service.log
#################################################################################

set -e  # Exit on error

# Configuration
SERVICE_NAME="Image Storage Service"
PYTHON_SCRIPT="main.py"
PID_FILE="service.pid"
LOG_DIR="logs"
LOG_FILE="${LOG_DIR}/service.log"
VENV_PATH="./venv/bin/activate"

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

check_if_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0  # Running
        else
            print_warning "PID file exists but process is not running. Cleaning up..."
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Main script
print_info "Starting ${SERVICE_NAME}..."

# Check if already running
if check_if_running; then
    PID=$(cat "$PID_FILE")
    print_error "Service is already running (PID: $PID)"
    print_info "Use './stop.sh' to stop it first"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_error "Python script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Create logs directory
mkdir -p "$LOG_DIR"
print_info "Log directory: $LOG_DIR"

# Activate virtual environment
if [ -f "$VENV_PATH" ]; then
    print_info "Activating virtual environment..."
    source "$VENV_PATH"
else
    print_warning "Virtual environment not found at $VENV_PATH"
    print_warning "Using system Python..."
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    print_info "Please create .env file from .env.example"
    exit 1
fi

# Start the service
print_info "Starting service in background..."
nohup python -u "$PYTHON_SCRIPT" >> "$LOG_FILE" 2>&1 &
SERVICE_PID=$!

# Save PID
echo "$SERVICE_PID" > "$PID_FILE"

# Wait a bit and check if process is still running
sleep 2
if ps -p "$SERVICE_PID" > /dev/null 2>&1; then
    print_info "${GREEN}✓${NC} Service started successfully!"
    print_info "PID: $SERVICE_PID"
    print_info "Log file: $LOG_FILE"
    print_info ""
    print_info "Commands:"
    print_info "  ./stop.sh          - Stop the service"
    print_info "  ./watch_logs.sh    - Watch logs in real-time"
    print_info "  ./status.sh        - Check service status"
    print_info ""
    print_info "Showing last 10 lines of log..."
    echo "----------------------------------------"
    tail -n 10 "$LOG_FILE"
else
    print_error "Service failed to start!"
    print_info "Check logs: $LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi

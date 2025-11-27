#!/bin/bash

#################################################################################
# Image Storage Service - Restart Script
#
# This script restarts the image storage service.
#################################################################################

# Configuration
SERVICE_NAME="Image Storage Service"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

# Header
echo ""
echo "========================================"
echo "  ${SERVICE_NAME}"
echo "  Restart"
echo "========================================"
echo ""

# Stop the service
print_info "Stopping service..."
./stop.sh

# Wait a bit
sleep 2

# Start the service
print_info "Starting service..."
./start.sh

echo ""
print_info "${GREEN}✓${NC} Restart complete"
echo ""

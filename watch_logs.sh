#!/bin/bash

#################################################################################
# Image Storage Service - Watch Logs Script
#
# This script displays logs in real-time with optional filtering.
#
# Usage:
#   ./watch_logs.sh              - Show all logs
#   ./watch_logs.sh ERROR        - Show only ERROR logs
#   ./watch_logs.sh INFO         - Show only INFO logs
#   ./watch_logs.sh -n 50        - Show last 50 lines first
#################################################################################

# Configuration
LOG_FILE="logs/service.log"
DEFAULT_LINES=20

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Usage: $0 [OPTIONS] [FILTER]"
    echo ""
    echo "Options:"
    echo "  -n NUMBER    Show last NUMBER lines before following"
    echo "  -h, --help   Show this help message"
    echo ""
    echo "Filters:"
    echo "  ERROR        Show only ERROR logs"
    echo "  WARNING      Show only WARNING logs"
    echo "  INFO         Show only INFO logs"
    echo "  DEBUG        Show only DEBUG logs"
    echo ""
    echo "Examples:"
    echo "  $0                     # Show all logs (last ${DEFAULT_LINES} lines)"
    echo "  $0 ERROR               # Show only errors"
    echo "  $0 -n 50               # Show last 50 lines then follow"
    echo "  $0 -n 100 WARNING      # Show last 100 lines of warnings"
    exit 0
}

# Parse arguments
LINES=$DEFAULT_LINES
FILTER=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -n)
            LINES="$2"
            shift 2
            ;;
        ERROR|WARNING|INFO|DEBUG)
            FILTER="$1"
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_help
            ;;
    esac
done

# Check if log file exists
if [ ! -f "$LOG_FILE" ]; then
    print_error "Log file not found: $LOG_FILE"
    print_info "Service may not be running yet."
    print_info "Start the service with: ./start.sh"
    exit 1
fi

# Display header
echo "=================================="
echo "  Image Storage Service - Logs"
echo "=================================="
echo "Log file: $LOG_FILE"
if [ -n "$FILTER" ]; then
    echo "Filter: $FILTER"
fi
echo "Lines: $LINES (then follow)"
echo "Press Ctrl+C to exit"
echo "=================================="
echo ""

# Watch logs with optional filter
if [ -n "$FILTER" ]; then
    print_info "Showing filtered logs (${FILTER})..."
    tail -n "$LINES" "$LOG_FILE" | grep --color=always "$FILTER"
    tail -f "$LOG_FILE" | grep --color=always "$FILTER"
else
    print_info "Showing all logs..."

    # Colorize output
    tail -n "$LINES" "$LOG_FILE" | \
        sed -e "s/ERROR/${RED}ERROR${NC}/g" \
            -e "s/WARNING/${YELLOW}WARNING${NC}/g" \
            -e "s/INFO/${GREEN}INFO${NC}/g" \
            -e "s/DEBUG/${BLUE}DEBUG${NC}/g"

    tail -f "$LOG_FILE" | \
        sed -e "s/ERROR/${RED}ERROR${NC}/g" \
            -e "s/WARNING/${YELLOW}WARNING${NC}/g" \
            -e "s/INFO/${GREEN}INFO${NC}/g" \
            -e "s/DEBUG/${BLUE}DEBUG${NC}/g"
fi

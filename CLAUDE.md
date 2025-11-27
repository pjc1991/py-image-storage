# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an image compression service that monitors a source directory for image files, compresses them using Pillow to WebP format, and moves them to a destination directory. The application uses watchdog for file system monitoring and implements async I/O for performance.

## Environment Setup

Create a `.env` file with required paths:
```
UNCOMPRESSED=\\NAS\FILES\uncompressed
COMPRESSED=\\NAS\FILES\compressed
CLEANUP_INTERVAL_SECONDS=60
MIN_FILE_SIZE_KB=1024
```

## Key Commands

### Development
```bash
# Install dependencies
pip3 install -r requirements.txt

# Run application
python observer.py

# Start with nohup (production)
./start.sh

# Stop application
./stop.sh

# Watch logs
./watch_logs.sh
```

### Testing
```bash
# Run specific test
python -m pytest tests/test_<name>.py

# Run all tests
python -m pytest tests/
```

## Architecture

**Entry Point**: `observer.py`
- Main event loop that coordinates all operations
- Handles initial file scanning and directory observation
- Manages periodic cleanup tasks

**Core Components**:
- `file_handler.py`: File system event handling, file readiness checking, and core file processing logic
- `image_handler.py`: Image compression using Pillow (JPEG/PNG → WebP)
- `task_handler.py`: Multiple task execution strategies (asyncio, multiprocessing, semaphores)

**Key Features**:
- Files in root directory get organized into YYYY-MM subdirectories based on modification time
- Duplicate event filtering using TTL cache
- File readiness detection (waits for copy completion)
- Multiple task processing modes via `TaskHandleType` enum
- Automatic cleanup of empty directories
- Configurable minimum file size threshold

**File Processing Flow**:
1. File system events trigger via watchdog
2. Events queued for processing with deduplication
3. Files checked for readiness and type
4. Images compressed to WebP, non-images moved as-is
5. Original files deleted after successful processing
6. Empty directories cleaned up automatically
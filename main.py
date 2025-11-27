#!/usr/bin/env python3
"""
Image Storage Service - Main Entry Point

This service monitors a directory for image files, compresses them to WebP format,
and moves them to a destination directory.

Usage:
    python main.py

Configuration:
    Create a .env file with required settings (see .env.example)

Architecture:
    - ImageCompressor: Handles image compression
    - FileProcessor: Manages file processing workflow
    - FileWatcher: Monitors filesystem for changes
    - Application: Orchestrates all components
"""
import asyncio
import sys

from application import main

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\nShutdown complete')
        sys.exit(0)
    except Exception as e:
        print(f'Fatal error: {e}')
        sys.exit(1)

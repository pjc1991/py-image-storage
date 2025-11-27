import asyncio
import os
from asyncio import Queue
from datetime import datetime

from watchdog.observers import Observer

import task_handler
from config import Config
from file_handler import FileChangeHandler
from logger import get_logger

logger = get_logger(__name__)


async def periodic_cleanup(dir_path: str, new_dir_path: str, queue: Queue, config: Config):
    interval = config.cleanup_interval_seconds
    logger.info(f'Starting periodic cleanup every {interval} seconds')
    while True:
        await asyncio.sleep(interval)
        logger.info('Running periodic cleanup')
        
        # 1. Scan for remaining files (similar to initial_file_handle)
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Skip if file is currently being written to (simple check, handle_file does more)
                if not os.path.exists(file_path):
                    continue

                try:
                    if dir_path == root:
                        yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                        new_file_path = os.path.join(new_dir_path, yyyy_mm, file)
                    else:
                        new_file_path = file_path.replace(dir_path, new_dir_path)

                    # Add to queue if not already there (cache check handles duplicates in handler,
                    # but we can just add it and let handler decide)
                    queue.put_nowait((file_path, new_file_path))
                except (OSError, FileNotFoundError) as e:
                    # File was deleted between exists check and getmtime call
                    logger.debug(f'File disappeared during cleanup scan: {file_path}')
                    continue

        # 2. Delete empty folders
        for root, dirs, files in os.walk(dir_path, topdown=False):
            if root == dir_path:
                continue
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                    logger.info(f'Removed empty directory: {root}')
                except OSError as e:
                    logger.debug(f'Could not remove directory {root}: {e}')
                    pass # Directory might not be empty or other error


async def observe_directory(dir_path: str, new_dir_path: str, queue_provided: Queue, config: Config) -> None:
    event_handler = FileChangeHandler(dir_path, new_dir_path, queue_provided)
    observer = Observer()
    observer.schedule(event_handler, dir_path, recursive=True)
    observer.start()
    logger.info(f'File system observer started for: {dir_path}')

    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup(dir_path, new_dir_path, queue_provided, config))
    
    try:
        while True:
            if not queue_provided.empty():
                await task_handler.handle_tasks(queue_provided)
            else:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info('Keyboard interrupt received, shutting down...')
        observer.stop()
        cleanup_task.cancel()
    observer.join()
    logger.info('Observer stopped')


async def initial_file_handle(uncompressed_path: str, compressed_path: str, que: Queue):
    logger.info('Starting initial file scan')
    file_count = 0

    for root, dirs, files in os.walk(uncompressed_path):
        if files:
            logger.debug(f'Found {len(files)} files in {root}')

        for file in files:
            file_path = os.path.join(root, file)
            try:
                if uncompressed_path == root and os.path.isfile(file_path):
                    yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                    logger.debug(f'File {file} is in root directory, organizing into {yyyy_mm}')
                    new_file_path = os.path.join(compressed_path, yyyy_mm, file)
                else:
                    new_file_path = file_path.replace(uncompressed_path, compressed_path)

                logger.debug(f'Queueing: {file_path} -> {new_file_path}')
                que.put_nowait((file_path, new_file_path))
                file_count += 1

            except (OSError, FileNotFoundError) as e:
                # File was deleted between directory scan and processing
                logger.warning(f'File disappeared before processing: {file_path}')
                continue

    logger.info(f'Initial scan complete, found {file_count} files to process')
    await task_handler.handle_tasks(que)
    logger.info('Initial file processing complete')

async def main():
    """Main async function that runs all async operations in a single event loop"""
    from config import Config, ConfigurationError
    from logger import setup_logging

    try:
        # Load and validate configuration
        config = Config.from_env()

        # Setup logging
        setup_logging(config.log_level)

        # Validate configuration
        config.validate()
        logger.info(f'Configuration loaded: {config}')

    except ConfigurationError as e:
        print(f'Configuration error: {e}')
        return

    queue = asyncio.Queue()

    # Check all files in the directory before starting
    logger.info(f'Monitoring: {config.uncompressed_path}')
    logger.info(f'Output to: {config.compressed_path}')

    await initial_file_handle(config.uncompressed_path, config.compressed_path, queue)

    # Start the observer
    logger.info('Starting directory observer')
    await observe_directory(config.uncompressed_path, config.compressed_path, queue, config)


if __name__ == "__main__":
    asyncio.run(main())

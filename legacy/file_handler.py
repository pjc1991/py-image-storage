import os
import time
import asyncio
from asyncio import Queue
from datetime import datetime

from cachetools import TTLCache
from watchdog.events import FileSystemEventHandler

from image_handler import async_compress_image
from logger import get_logger

logger = get_logger(__name__)


class FileChangeHandler(FileSystemEventHandler):
    dir_path: str = None
    new_dir_path: str = None
    queue: Queue = None
    cache = TTLCache(maxsize=100, ttl=60)

    def __init__(self, dir_path: str, new_dir_path: str, queue: Queue):
        self.dir_path = dir_path
        self.new_dir_path = new_dir_path
        self.queue = queue
        super().__init__()

    def is_key_cached(self, key: tuple) -> bool:
        return key in self.cache

    def on_modified(self, event):
        seconds = int(time.time())
        key = (seconds, event.src_path)
        if self.is_key_cached(key):
            logger.debug(f'Duplicate event ignored: {event.src_path}')
            return
        self.cache[key] = True
        file_path = event.src_path
        # if the file_path is in the uncompressed root directory
        # add the YYYY-MM directory to the new file path
        if self.dir_path == os.path.dirname(file_path) and os.path.isfile(file_path):
            file = os.path.basename(file_path)
            yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
            logger.debug(f'File {file} detected in root directory')
            new_file_path = os.path.join(self.new_dir_path, yyyy_mm, file)
        else:
            new_file_path = file_path.replace(self.dir_path, self.new_dir_path)
        self.queue.put_nowait((file_path, new_file_path))
        logger.debug(f'File queued: {file_path}')


async def wait_for_file_ready(file_path: str, timeout: int = 10, check_interval: float = 0.5) -> bool:
    """
    Wait until the file size stops changing, indicating the copy is complete.
    """
    last_size = -1
    start_time = time.time()

    while time.time() - start_time < timeout:
        if not os.path.exists(file_path):
            return False

        current_size = os.path.getsize(file_path)
        if current_size == last_size:
            return True

        last_size = current_size
        await asyncio.sleep(check_interval)

    logger.warning(f"Timeout waiting for file {file_path} to stabilize")
    return False


async def handle_file(file_path: str, new_file_path: str):
    """
    Handle a single file - check, compress if needed, and move to destination.

    This function must work in both async and multiprocessing contexts.
    It imports Config locally to work properly in multiprocessing workers.
    """
    # Import locally for multiprocessing compatibility
    import asyncio
    from config import Config

    try:
        # Load config in worker process
        config = Config.from_env()

        logger.debug(f'Processing file: {file_path}')

        if not os.path.exists(file_path):
            logger.debug(f'File does not exist: {file_path}')
            return

        # Skip if it's a directory, not a file
        if os.path.isdir(file_path):
            logger.debug(f'Skipping directory: {file_path}')
            return

        # Wait for file copy to finish
        if not await wait_for_file_ready(file_path):
            logger.warning(f"Skipping {file_path} - not ready or disappeared")
            return

        # Create destination directory if needed
        dest_dir = os.path.dirname(new_file_path)
        if not os.path.exists(dest_dir):
            logger.info(f'Creating directory: {dest_dir}')
            os.makedirs(dest_dir)

        # Check if already WebP
        if file_path.endswith('.webp'):
            logger.info(f'File already WebP, moving: {os.path.basename(file_path)}')
            os.rename(file_path, new_file_path)
            return

        # Check file size threshold
        file_size_bytes = os.path.getsize(file_path)
        file_size_kb = file_size_bytes / 1024
        if file_size_bytes < config.min_file_size_kb * 1024:
            logger.info(f'File too small ({file_size_kb:.1f}KB), moving without compression: {os.path.basename(file_path)}')
            os.rename(file_path, new_file_path)
            return

        # Check if it's a compressible image
        if not file_path.endswith(('.jpg', '.jpeg', '.png')):
            logger.info(f'Not an image, moving without compression: {os.path.basename(file_path)}')
            os.rename(file_path, new_file_path)
        else:
            # Compress the image
            try:
                logger.info(f'Compressing {os.path.basename(file_path)} ({file_size_kb:.1f}KB)')
                await async_compress_image(file_path, new_file_path, config)
                logger.info(f'Compressed: {os.path.basename(file_path)}')

                # Remove original file
                os.remove(file_path)
                logger.debug(f'Removed original file: {file_path}')

            except Exception as e:
                logger.error(f'Compression failed for {file_path}: {e}')
                return

        # Clean up empty directories
        parent_dir = os.path.dirname(file_path)
        if not os.listdir(parent_dir) and \
                os.path.normpath(parent_dir) != os.path.normpath(config.uncompressed_path):
            os.rmdir(parent_dir)
            logger.info(f'Removed empty directory: {parent_dir}')

    except Exception as e:
        logger.error(f'Error handling file {file_path}: {e}', exc_info=True)

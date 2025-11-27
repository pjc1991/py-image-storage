"""
File system watcher module.
Handles monitoring directories for file changes.
"""
import asyncio
import os
import time
from asyncio import Queue
from datetime import datetime

from cachetools import TTLCache
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from config import Config
from logger import get_logger

logger = get_logger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Handles file system events from watchdog.

    Responsibilities:
    - React to file system changes
    - Filter duplicate events
    - Queue files for processing
    - Organize files into date-based directories
    """

    def __init__(self, config: Config, queue: Queue):
        """
        Initialize the event handler.

        Args:
            config: Application configuration
            queue: Queue to send file paths for processing
        """
        super().__init__()
        self.config = config
        self.queue = queue
        self.cache = TTLCache(maxsize=100, ttl=60)
        logger.debug('FileEventHandler initialized')

    def _is_duplicate_event(self, event_path: str) -> bool:
        """
        Check if this is a duplicate event within the cache window.

        Args:
            event_path: Path from the event

        Returns:
            True if duplicate, False if new
        """
        seconds = int(time.time())
        key = (seconds, event_path)
        if key in self.cache:
            return True
        self.cache[key] = True
        return False

    def _calculate_destination_path(self, source_path: str) -> str:
        """
        Calculate destination path for a file.

        For files in the root uncompressed directory, organize into YYYY-MM subdirectories.
        For files in subdirectories, maintain the structure.

        Args:
            source_path: Source file path

        Returns:
            Destination file path
        """
        source_dir = os.path.dirname(source_path)
        file_name = os.path.basename(source_path)

        # Check if file is in root directory
        if source_dir == self.config.uncompressed_path and os.path.isfile(source_path):
            # Organize into YYYY-MM directory
            try:
                mtime = os.path.getmtime(source_path)
                yyyy_mm = datetime.fromtimestamp(mtime).strftime('%Y-%m')
                dest_path = os.path.join(self.config.compressed_path, yyyy_mm, file_name)
                logger.debug(f'Root file will be organized into {yyyy_mm}: {file_name}')
                return dest_path
            except OSError:
                # If we can't get mtime, just mirror the structure
                pass

        # Mirror directory structure
        return source_path.replace(self.config.uncompressed_path, self.config.compressed_path)

    def on_modified(self, event):
        """
        Handle file modification events.

        Args:
            event: File system event from watchdog
        """
        if event.is_directory:
            return

        source_path = event.src_path

        # Filter duplicate events
        if self._is_duplicate_event(source_path):
            logger.debug(f'Duplicate event ignored: {source_path}')
            return

        # Calculate destination
        dest_path = self._calculate_destination_path(source_path)

        # Queue for processing
        self.queue.put_nowait((source_path, dest_path))
        logger.debug(f'File queued: {os.path.basename(source_path)}')


class FileWatcher:
    """
    Watches file system for changes and coordinates processing.

    Responsibilities:
    - Start/stop file system observer
    - Manage periodic cleanup tasks
    - Coordinate queue processing
    """

    def __init__(self, config: Config, processor):
        """
        Initialize the file watcher.

        Args:
            config: Application configuration
            processor: FileProcessor instance
        """
        self.config = config
        self.processor = processor
        self.queue: Queue = asyncio.Queue()
        self.observer: Optional[Observer] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        logger.debug('FileWatcher initialized')

    async def scan_initial_files(self) -> int:
        """
        Scan for existing files in the uncompressed directory.

        Returns:
            Number of files found
        """
        logger.info('Starting initial file scan')
        file_count = 0

        for root, dirs, files in os.walk(self.config.uncompressed_path):
            if files:
                logger.debug(f'Scanning: {root} ({len(files)} files)')

            for file in files:
                file_path = os.path.join(root, file)

                try:
                    # Skip if not a file
                    if not os.path.isfile(file_path):
                        continue

                    # Calculate destination
                    if root == self.config.uncompressed_path:
                        # Organize into YYYY-MM directory
                        yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                        dest_path = os.path.join(self.config.compressed_path, yyyy_mm, file)
                    else:
                        # Mirror directory structure
                        dest_path = file_path.replace(
                            self.config.uncompressed_path,
                            self.config.compressed_path
                        )

                    # Queue for processing
                    self.queue.put_nowait((file_path, dest_path))
                    file_count += 1

                except (OSError, FileNotFoundError) as e:
                    logger.warning(f'File disappeared during scan: {file_path}')
                    continue

        logger.info(f'Initial scan complete: found {file_count} files')
        return file_count

    async def process_queue(self) -> None:
        """
        Process all files currently in the queue.
        """
        if self.queue.empty():
            return

        # Collect all queued files
        file_pairs = []
        while not self.queue.empty():
            try:
                file_pair = self.queue.get_nowait()
                file_pairs.append(file_pair)
            except asyncio.QueueEmpty:
                break

        # Deduplicate by source path to prevent race conditions
        # Keep the last occurrence of each source file
        seen = {}
        for source, dest in file_pairs:
            seen[source] = dest

        file_pairs = [(source, dest) for source, dest in seen.items()]

        if len(file_pairs) < len(seen):
            logger.debug(f'Deduplicated queue: {len(seen)} → {len(file_pairs)} unique files')

        # Process batch
        if file_pairs:
            await self.processor.process_batch(file_pairs)

    async def periodic_cleanup(self) -> None:
        """
        Periodically scan for missed files and clean up empty directories.
        """
        interval = self.config.cleanup_interval_seconds
        logger.info(f'Starting periodic cleanup (every {interval}s)')

        while True:
            await asyncio.sleep(interval)
            logger.info('Running periodic cleanup')

            try:
                # Scan for any files that were missed
                file_count = 0
                for root, dirs, files in os.walk(self.config.uncompressed_path):
                    for file in files:
                        file_path = os.path.join(root, file)

                        if not os.path.exists(file_path):
                            continue

                        try:
                            # Calculate destination
                            if root == self.config.uncompressed_path:
                                yyyy_mm = datetime.fromtimestamp(
                                    os.path.getmtime(file_path)
                                ).strftime('%Y-%m')
                                dest_path = os.path.join(self.config.compressed_path, yyyy_mm, file)
                            else:
                                dest_path = file_path.replace(
                                    self.config.uncompressed_path,
                                    self.config.compressed_path
                                )

                            self.queue.put_nowait((file_path, dest_path))
                            file_count += 1

                        except (OSError, FileNotFoundError):
                            continue

                if file_count > 0:
                    logger.info(f'Cleanup found {file_count} files to process')

                # Clean up empty directories
                self._cleanup_empty_directories()

            except Exception as e:
                logger.error(f'Error in periodic cleanup: {e}', exc_info=True)

    def _cleanup_empty_directories(self) -> None:
        """
        Remove empty directories in the uncompressed path.
        """
        removed_count = 0

        for root, dirs, files in os.walk(self.config.uncompressed_path, topdown=False):
            # Skip root directory
            if root == self.config.uncompressed_path:
                continue

            # Check if empty and remove
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                    logger.info(f'Removed empty directory: {root}')
                    removed_count += 1
                except OSError as e:
                    logger.debug(f'Could not remove directory {root}: {e}')

        if removed_count > 0:
            logger.info(f'Removed {removed_count} empty directories')

    async def start(self) -> None:
        """
        Start watching the file system.
        """
        # Create event handler
        event_handler = FileEventHandler(self.config, self.queue)

        # Start observer
        self.observer = Observer()
        self.observer.schedule(
            event_handler,
            self.config.uncompressed_path,
            recursive=True
        )
        self.observer.start()
        logger.info(f'File system observer started: {self.config.uncompressed_path}')

        # Start periodic cleanup
        self.cleanup_task = asyncio.create_task(self.periodic_cleanup())

        # Main processing loop
        try:
            while True:
                # Process any queued files
                await self.process_queue()

                # Sleep briefly
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info('File watcher cancelled')
            raise

    async def stop(self) -> None:
        """
        Stop watching the file system.
        """
        logger.info('Stopping file watcher')

        # Stop cleanup task
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Stop observer
        if self.observer:
            self.observer.stop()
            self.observer.join()

        logger.info('File watcher stopped')

"""
File processing module.
Handles the workflow of processing individual files.
"""
import asyncio
import os
import time
from datetime import datetime
from typing import Optional

from config import Config
from compressor import ImageCompressor
from logger import get_logger

logger = get_logger(__name__)


class FileProcessor:
    """
    Handles file processing workflow.

    Responsibilities:
    - Wait for files to be ready
    - Determine what to do with each file (compress, move, skip)
    - Coordinate with ImageCompressor for compression
    - Clean up empty directories
    """

    def __init__(self, config: Config, compressor: ImageCompressor):
        """
        Initialize the file processor.

        Args:
            config: Application configuration
            compressor: Image compressor instance
        """
        self.config = config
        self.compressor = compressor
        # Semaphore to limit concurrent compressions
        self.semaphore = asyncio.Semaphore(config.max_concurrent_compressions)
        logger.debug(f'FileProcessor initialized (max concurrent: {config.max_concurrent_compressions})')

    async def wait_for_file_ready(
        self,
        file_path: str,
        timeout: int = 10,
        check_interval: float = 0.5
    ) -> bool:
        """
        Wait until file size stops changing, indicating copy is complete.

        Args:
            file_path: Path to file to check
            timeout: Maximum seconds to wait
            check_interval: Seconds between checks

        Returns:
            True if file is ready, False if timeout or file disappeared
        """
        last_size = -1
        start_time = time.time()

        while time.time() - start_time < timeout:
            if not os.path.exists(file_path):
                logger.debug(f'File disappeared while waiting: {file_path}')
                return False

            try:
                current_size = os.path.getsize(file_path)
                if current_size == last_size and current_size > 0:
                    logger.debug(f'File ready: {file_path} ({current_size} bytes)')
                    return True

                last_size = current_size
                await asyncio.sleep(check_interval)

            except OSError as e:
                logger.debug(f'Error checking file size: {e}')
                return False

        logger.warning(f'Timeout waiting for file to stabilize: {file_path}')
        return False

    async def process_file(self, source_path: str, dest_path: str) -> bool:
        """
        Process a single file through the complete workflow.

        Args:
            source_path: Source file path
            dest_path: Destination file path

        Returns:
            True if successfully processed, False otherwise
        """
        # Use semaphore to limit concurrent processing
        async with self.semaphore:
            try:
                logger.debug(f'Processing: {source_path}')

                # Check if file exists
                if not os.path.exists(source_path):
                    logger.debug(f'File does not exist: {source_path}')
                    return False

                # Skip directories
                if os.path.isdir(source_path):
                    logger.debug(f'Skipping directory: {source_path}')
                    return False

                # Skip if destination already exists (performance optimization)
                if self.config.skip_existing_files:
                    # Check for both original extension and .webp extension
                    dest_path_webp = self.compressor._ensure_webp_extension(dest_path)
                    if os.path.exists(dest_path) or os.path.exists(dest_path_webp):
                        logger.debug(f'Destination already exists, skipping: {dest_path}')
                        # Remove source file since destination exists
                        if os.path.exists(source_path):
                            os.remove(source_path)
                            logger.debug(f'Removed source (destination exists): {source_path}')
                        return True

                # Wait for file to be ready
                if not await self.wait_for_file_ready(source_path):
                    logger.warning(f'File not ready, skipping: {source_path}')
                    return False

                # Create destination directory if needed
                dest_dir = os.path.dirname(dest_path)
                if not os.path.exists(dest_dir):
                    logger.info(f'Creating directory: {dest_dir}')
                    os.makedirs(dest_dir, exist_ok=True)

                # Determine action based on file type
                file_name = os.path.basename(source_path)

                # Already WebP - just move
                if source_path.lower().endswith('.webp'):
                    logger.info(f'Already WebP, moving: {file_name}')
                    os.rename(source_path, dest_path)
                    return True

                # Should compress?
                if self.compressor.should_compress(source_path):
                    # Compress the image
                    success = await self.compressor.compress(source_path, dest_path)
                    if success:
                        # Remove original after successful compression
                        # Double-check file still exists before removing
                        if os.path.exists(source_path):
                            os.remove(source_path)
                            logger.debug(f'Removed original: {source_path}')
                        else:
                            logger.warning(f'Original file already removed: {source_path}')
                    else:
                        logger.error(f'Compression failed, keeping original: {source_path}')
                        return False
                else:
                    # Not an image or too small - just move
                    file_size_kb = os.path.getsize(source_path) / 1024
                    logger.info(f'Moving without compression: {file_name} ({file_size_kb:.1f}KB)')
                    os.rename(source_path, dest_path)

                # Clean up empty directories
                self._cleanup_empty_directory(source_path)

                return True

            except Exception as e:
                logger.error(f'Error processing file {source_path}: {e}', exc_info=True)
                return False

    def _cleanup_empty_directory(self, file_path: str) -> None:
        """
        Remove empty parent directory if not the root uncompressed directory.

        Args:
            file_path: Path to file that was processed
        """
        try:
            parent_dir = os.path.dirname(file_path)

            # Don't remove the root uncompressed directory
            if os.path.normpath(parent_dir) == os.path.normpath(self.config.uncompressed_path):
                return

            # Check if empty and remove
            if os.path.exists(parent_dir) and not os.listdir(parent_dir):
                os.rmdir(parent_dir)
                logger.info(f'Removed empty directory: {parent_dir}')

        except Exception as e:
            logger.debug(f'Could not remove directory {parent_dir}: {e}')

    async def process_batch(self, file_pairs: list[tuple[str, str]]) -> dict[str, int]:
        """
        Process multiple files concurrently.

        Args:
            file_pairs: List of (source_path, dest_path) tuples

        Returns:
            Dictionary with 'success' and 'failed' counts
        """
        if not file_pairs:
            return {'success': 0, 'failed': 0}

        logger.info(f'Processing batch of {len(file_pairs)} files')

        tasks = [
            self.process_file(source, dest)
            for source, dest in file_pairs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        failed_count = len(results) - success_count

        logger.info(f'Batch complete: {success_count} succeeded, {failed_count} failed')

        return {
            'success': success_count,
            'failed': failed_count
        }

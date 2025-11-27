"""
Image compression module using libvips.

libvips is 4-10x faster than PIL for image operations and uses less memory.
"""
import asyncio
import os
from pathlib import Path
from typing import Optional

try:
    import pyvips
except ImportError:
    raise ImportError(
        "pyvips is required. Install with:\n"
        "  System: sudo apt install libvips-dev (Ubuntu/Debian)\n"
        "  Python: pip install pyvips"
    )

from cachetools import TTLCache

from config import Config
from logger import get_logger

logger = get_logger(__name__)


class ImageCompressor:
    """
    Handles image compression operations using libvips.

    Responsibilities:
    - Compress images to WebP format (2-8x faster than PIL)
    - Resize images if needed
    - Cache compression operations to avoid duplicates
    - Use streaming for low memory usage
    """

    def __init__(self, config: Config):
        """
        Initialize the image compressor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.cache = TTLCache(maxsize=config.cache_maxsize, ttl=config.cache_ttl)
        logger.debug(f'ImageCompressor (libvips) initialized with cache size={config.cache_maxsize}, ttl={config.cache_ttl}')

    def _compress_sync(self, source_path: str, dest_path: str) -> bool:
        """
        Synchronously compress an image file using libvips.

        Args:
            source_path: Source image file path
            dest_path: Destination WebP file path

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if source file still exists
            if not os.path.exists(source_path):
                logger.warning(f'Source file no longer exists: {source_path}')
                return False

            # Load image with libvips
            # access='sequential' enables streaming (low memory usage)
            img = pyvips.Image.new_from_file(source_path, access='sequential')

            original_width = img.width
            original_height = img.height
            logger.debug(f'Image: {original_width}x{original_height}')

            # Resize if image is too large
            max_res = self.config.max_resolution
            if img.width > max_res or img.height > max_res:
                # thumbnail_image maintains aspect ratio and is very fast
                logger.debug(f'Resizing from {img.width}x{img.height} to max {max_res}px')
                img = img.thumbnail_image(max_res, height=max_res)

            # Save as WebP
            # Q = quality (0-100)
            # strip = remove metadata (smaller files, faster)
            # effort = compression effort (0-6, 4 is balanced)
            img.write_to_file(
                dest_path,
                Q=self.config.compression_quality,
                strip=True,
                effort=4  # Balance between speed and compression
            )

            # Log compression results
            original_size = os.path.getsize(source_path)
            compressed_size = os.path.getsize(dest_path)
            savings = (1 - compressed_size / original_size) * 100

            logger.info(
                f'Compressed: {os.path.basename(source_path)} '
                f'({original_size/1024:.1f}KB → {compressed_size/1024:.1f}KB, '
                f'{savings:.1f}% saved)'
            )

            return True

        except pyvips.Error as e:
            logger.error(f'libvips error compressing {source_path}: {e}')
            return False
        except Exception as e:
            logger.error(f'Compression failed for {source_path}: {e}')
            return False

    async def compress(self, source_path: str, dest_path: str) -> bool:
        """
        Asynchronously compress an image file.

        Args:
            source_path: Source image file path
            dest_path: Destination file path (will be converted to .webp)

        Returns:
            True if successful, False otherwise
        """
        # Check cache to avoid duplicate compressions
        cache_key = (source_path, dest_path)
        if cache_key in self.cache:
            logger.debug(f'Duplicate compression request ignored (cached): {source_path}')
            return True

        # Mark as processing
        self.cache[cache_key] = True

        # Ensure destination has .webp extension
        dest_path_webp = self._ensure_webp_extension(dest_path)

        logger.debug(f'Starting compression: {source_path} → {dest_path_webp}')

        # Run compression in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._compress_sync,
            source_path,
            dest_path_webp
        )

        return result

    def _ensure_webp_extension(self, path: str) -> str:
        """
        Ensure the path has .webp extension.

        Args:
            path: File path

        Returns:
            Path with .webp extension
        """
        base, _ = os.path.splitext(path)
        return base + '.webp'

    def should_compress(self, file_path: str) -> bool:
        """
        Determine if a file should be compressed.

        Args:
            file_path: Path to check

        Returns:
            True if the file should be compressed
        """
        # Check if it's a compressible image format
        if not file_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            return False

        # Check file size threshold
        try:
            file_size = os.path.getsize(file_path)
            if file_size < self.config.min_file_size_kb * 1024:
                logger.debug(
                    f'File too small to compress ({file_size/1024:.1f}KB < '
                    f'{self.config.min_file_size_kb}KB): {file_path}'
                )
                return False
        except OSError:
            return False

        return True

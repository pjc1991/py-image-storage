import asyncio

from PIL import Image
from cachetools import TTLCache

from logger import get_logger

logger = get_logger(__name__)

# Cache will be initialized with config values
compression_cache = None


def compress_image(file_path: str, new_file_path: str, config) -> bool:
    """
    Read image from file_path, compress it by max_resolution,
    while keeping the aspect ratio, and save it to new_file_path
    in WebP format.

    Args:
        file_path: Source image path
        new_file_path: Destination path (will be .webp)
        config: Configuration object with max_resolution and compression_quality

    Returns:
        True if successful, False otherwise
    """
    try:
        with Image.open(file_path) as img:
            # Validate image format
            if img.format not in ('JPEG', 'PNG'):
                logger.warning(f'Unsupported image format {img.format} for {file_path}')
                return False

            original_size = img.size
            logger.debug(f'Image size: {img.width}x{img.height}, format: {img.format}')

            # Resize if image is too large
            if img.height > config.max_resolution or img.width > config.max_resolution:
                logger.debug(f'Resizing from {img.width}x{img.height} to fit {config.max_resolution}px')
                img.thumbnail((config.max_resolution, config.max_resolution))

            # Save as WebP
            img.save(new_file_path, 'webp', quality=config.compression_quality)
            logger.debug(f'Saved as WebP with quality {config.compression_quality}')
            return True

    except Exception as e:
        logger.error(f'Failed to compress image {file_path}: {e}')
        return False


async def async_compress_image(file_path: str, new_file_path: str, config) -> None:
    """
    Asynchronously compress an image file.

    Args:
        file_path: Source image path
        new_file_path: Destination path
        config: Configuration object

    This function uses a cache to avoid duplicate compressions and runs
    the actual compression in a thread pool executor to avoid blocking
    the async event loop.
    """
    global compression_cache

    # Initialize cache if needed
    if compression_cache is None:
        from cachetools import TTLCache
        compression_cache = TTLCache(maxsize=config.cache_maxsize, ttl=config.cache_ttl)

    # Check if this file pair has already been processed recently
    cache_key = (file_path, new_file_path)
    if cache_key in compression_cache:
        logger.debug(f'Duplicate compression request ignored: {file_path}')
        return

    compression_cache[cache_key] = True

    # Ensure destination has .webp extension
    import os
    base, _ = os.path.splitext(new_file_path)
    new_file_path_with_extension = base + '.webp'

    logger.debug(f'Starting async compression: {file_path} -> {new_file_path_with_extension}')

    # Run compression in thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, compress_image, file_path, new_file_path_with_extension, config)

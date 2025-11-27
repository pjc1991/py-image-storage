import asyncio

from PIL import Image
from cachetools import TTLCache, cached

compression_cache = TTLCache(maxsize=100, ttl=60)


def compress_image(file_path: str, new_file_path: str, max_resolution: int = 1920, quality: int = 90) -> bool:
    """
    read image from file_path, compress it by max_resolution,
    while keeping the aspect ratio, and save it to file_path
    on WebP format.
    """
    with Image.open(file_path) as img:
        # exception handling
        if img.format != 'JPEG' and img.format != 'PNG':
            return False

        if img is None:
            return False

        # if the image is too large, resize it
        if img.height > max_resolution or img.width > max_resolution:
            img.thumbnail((max_resolution, max_resolution))

        img.save(new_file_path, 'webp', quality=quality)
        return True


async def async_compress_image(file_path: str, new_file_path: str) -> None:
    # Check if this file pair has already been processed recently
    cache_key = (file_path, new_file_path)
    if cache_key in compression_cache:
        # print(f'duplicate event: {file_path} on async_compress_image')
        return
    compression_cache[cache_key] = True
    import os
    base, _ = os.path.splitext(new_file_path)
    new_file_path_with_extension_replaced = base + '.webp'
    print(f'Compressing {file_path} to {new_file_path_with_extension_replaced}')
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, compress_image, file_path, new_file_path_with_extension_replaced)

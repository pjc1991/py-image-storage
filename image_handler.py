import asyncio
import concurrent.futures

from PIL import Image


def compress_image(file_path: str, new_file_path: str, max_resolution: int = 1920, quality: int = 80) -> bool:
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
    with concurrent.futures.ThreadPoolExecutor() as pool:
        await asyncio.get_event_loop().run_in_executor(
            pool, compress_image, file_path, new_file_path
        )

import os
import time
import asyncio
from asyncio import Queue
from datetime import datetime

from cachetools import TTLCache
from watchdog.events import FileSystemEventHandler

from image_handler import async_compress_image


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
            # print(f'duplicate event: {event.src_path}')
            return
        self.cache[key] = True
        file_path = event.src_path
        # if the file_path is in the uncompressed root directory
        # add the YYYY-MM directory to the new file path
        if self.dir_path == os.path.dirname(file_path) and os.path.isfile(file_path):
            file = os.path.basename(file_path)
            yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
            print(f'File {file} is in the root directory')
            new_file_path = os.path.join(self.new_dir_path, yyyy_mm, file)
        else:
            new_file_path = file_path.replace(self.dir_path, self.new_dir_path)
        self.queue.put_nowait((file_path, new_file_path))


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
    
    print(f"Timeout waiting for file {file_path} to stabilize.")
    return False


async def handle_file(file_path: str, new_file_path: str):
    try:
        # print(f'handling file {file_path}')
        if not os.path.exists(file_path):
            # print(f'File {file_path} does not exist')
            return

        # Skip if it's a directory, not a file
        if os.path.isdir(file_path):
            # print(f'{file_path} is a directory, skipping')
            return

        # Wait for file copy to finish
        if not await wait_for_file_ready(file_path):
            print(f"Skipping {file_path} as it is not ready or disappeared.")
            return

        if not os.path.exists(os.path.dirname(new_file_path)):
            print(f'Creating directory {os.path.dirname(new_file_path)}')
            os.makedirs(os.path.dirname(new_file_path))

        if file_path.endswith('.webp'):
            print(f'File {file_path} is already compressed')
            os.rename(file_path, new_file_path)
            # print(f'File {file_path} has been moved to {new_file_path} '
            #       f'at {datetime.now()}')
            return

        # if the file is already smaller than MIN_FILE_SIZE_KB, do not compress it
        try:
            min_size_kb = int(os.getenv('MIN_FILE_SIZE_KB', 1024))
        except (ValueError, TypeError):
            print(f'Invalid MIN_FILE_SIZE_KB value, using default: 1024')
            min_size_kb = 1024

        if os.path.getsize(file_path) < min_size_kb * 1024:
            print(f'File {file_path} is smaller than {min_size_kb}KB')
            os.rename(file_path, new_file_path)
            # print(f'File {file_path} has been moved to {new_file_path} '
            #       f'at {datetime.now()}')
            return

        if not file_path.endswith(('.jpg', '.jpeg', '.png')):
            print(f'File {file_path} is not an image, moving without conversion')
            os.rename(file_path, new_file_path)
            print(f'File {file_path} has been moved to {new_file_path} '
                  f'at {datetime.now()}')
        else:
            try:
                print(f'Compressing file {file_path} to {new_file_path}')
                await async_compress_image(file_path, new_file_path)
            except Exception as e:
                print(f'Error while compressing file {file_path}: {e}')
                return
            compress_time = datetime.now()
            # log the event with timestamp
            print(f'File {file_path} has been compressed to {new_file_path} '
                  f'at {compress_time}')

            # remove the original file
            os.remove(file_path)
            remove_time = datetime.now()
            print(f'File {file_path} has been removed at {remove_time}')

        # delete the directory if it is empty
        parent_dir = os.path.dirname(file_path)
        uncompressed_dir = os.getenv('UNCOMPRESSED')
        if not os.listdir(parent_dir) and \
                os.path.normpath(parent_dir) != os.path.normpath(uncompressed_dir):
            os.rmdir(parent_dir)
            print(f'Directory {parent_dir} has been removed '
                  f'at {datetime.now()}')

    except Exception as e:
        print(f'Error while handling file {file_path}: {e}')

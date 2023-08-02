import os
import time
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


async def handle_file(file_path: str, new_file_path: str):
    try:
        # print(f'handling file {file_path}')
        if not os.path.exists(file_path):
            # print(f'File {file_path} does not exist')
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

        # if the file is already smaller than 1MB, do not compress it
        if os.path.getsize(file_path) < 1024 * 1024:
            print(f'File {file_path} is smaller than 1MB')
            os.rename(file_path, new_file_path)
            # print(f'File {file_path} has been moved to {new_file_path} '
            #       f'at {datetime.now()}')
            return

        if not file_path.endswith(('.jpg', '.jpeg', '.png')):
            print(f'File {file_path} is not an image')
            return

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
        if not os.listdir(os.path.dirname(file_path)) and \
                os.path.dirname(file_path) != os.getenv('UNCOMPRESSED'):
            os.rmdir(os.path.dirname(file_path))
            print(f'Directory {os.path.dirname(file_path)} has been removed '
                  f'at {datetime.now()}')

    except Exception as e:
        print(f'Error while handling file {file_path}: {e}')

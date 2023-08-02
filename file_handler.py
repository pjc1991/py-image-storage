import os
from datetime import datetime

from watchdog.events import FileSystemEventHandler

from image_handler import compress_image


class FileChangeHandler(FileSystemEventHandler):
    dir_path: str = None
    new_dir_path: str = None

    def __init__(self, dir_path: str, new_dir_path: str):
        self.dir_path = dir_path
        self.new_dir_path = new_dir_path
        super().__init__()

    def on_modified(self, event):
        file_path = event.src_path
        new_file_path = file_path.replace(self.dir_path, self.new_dir_path)
        handle_file(event.src_path, new_file_path)


def handle_file(file_path: str, new_file_path: str) -> None:

    if not os.path.exists(file_path):
        return

    if not os.path.exists(os.path.dirname(new_file_path)):
        os.makedirs(os.path.dirname(new_file_path))

    if os.path.exists(new_file_path):
        return

    if not file_path.endswith(('.jpg', '.jpeg', '.png')):
        return

    if file_path.endswith('.webp'):
        os.rename(file_path, new_file_path)
        print(f'File {file_path} has been moved to {new_file_path} '
              f'at {datetime.now()}')
        return

    try:
        compress_image(file_path, new_file_path)
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
    print(f'File {file_path} has been removed '
          f'at {remove_time}')

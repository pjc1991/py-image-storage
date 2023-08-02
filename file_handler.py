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
        if event.is_directory:
            return
        elif event.src_path.endswith(('.jpg', '.jpeg', '.png')):
            new_file_path = event.src_path.replace(self.dir_path, self.new_dir_path)
            try:
                compress_image(event.src_path, new_file_path)
            except Exception as e:
                print(f'Error while compressing file {event.src_path}: {e}')
                return
            compress_time = datetime.now()
            # log the event with timestamp
            print(f'File {event.src_path} has been compressed to {new_file_path} '
                  f'at {event.event_type} {compress_time}')

            # remove the original file
            os.remove(event.src_path)
            remove_time = datetime.now()
            print(f'File {event.src_path} has been removed '
                  f'at {event.event_type} {remove_time}')


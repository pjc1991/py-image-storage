import os

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
            compress_image(event.src_path, new_file_path)
            # log the event with timestamp
            print(f'File {event.src_path} has been compressed to {new_file_path} '
                  f'at {event.event_type} {event.time_created}')

            # remove the original file
            os.remove(event.src_path)
            print(f'File {event.src_path} has been removed '
                  f'at {event.event_type} {event.time_created}')


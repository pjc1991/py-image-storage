import os
import time
from datetime import datetime

from dotenv import load_dotenv
from watchdog.observers import Observer

from file_handler import FileChangeHandler, handle_file

load_dotenv()


def observe_directory(dir_path: str, new_dir_path: str) -> None:
    event_handler = FileChangeHandler(dir_path, new_dir_path)
    observer = Observer()
    observer.schedule(event_handler, dir_path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


uncompressed = os.getenv('UNCOMPRESSED')
compressed = os.getenv('COMPRESSED')

# check all files in the directory before starting
print(f'Checking files in {uncompressed}')
print(f'Compressed files will be stored in {compressed}'
      f'if they are not already there'
      f'and the original files will be removed'
      f'from {uncompressed}'
      f'if they are not already removed'
      f'at {datetime.now()}')

# the number of files in the directory
print(f'Number of files in {uncompressed}: '
      f'{len(os.listdir(uncompressed))}')

for file in os.listdir(uncompressed):
    if file.endswith(('.jpg', '.jpeg', '.png')):
        print(f'Handling file {file}')
        old_file_path = os.path.join(uncompressed, file)
        new_file_path = os.path.join(compressed, file)

        print(f'Old file path: {old_file_path}')
        print(f'New file path: {new_file_path}')
        handle_file(old_file_path, new_file_path)

# call the function
observe_directory(uncompressed, compressed)

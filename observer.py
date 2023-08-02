import asyncio
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
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


uncompressed = os.getenv('UNCOMPRESSED')
compressed = os.getenv('COMPRESSED')

# check all files in the directory before starting
print(f'Checking files in {uncompressed}')
print(f'Compressed files will be stored in {compressed}')

# the number of files in the directory
print('--- searching for files ---')

# find the files in the directory including subdirectories
for root, dirs, files in os.walk(uncompressed):
    print(f'Files in {root}: {files}')
    for file in files:
        print(f'File: {file}')
        file_path = os.path.join(root, file)
        new_file_path = file_path.replace(uncompressed, compressed)
        handle_file(file_path, new_file_path)

print('--- finished searching for files ---')

print('--- starting observer ---')
# call the function
observe_directory(uncompressed, compressed)

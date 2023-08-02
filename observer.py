import os
import time

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
for file in os.listdir(uncompressed):
    if file.endswith(('.jpg', '.jpeg', '.png')):
        handle_file(os.path.join(uncompressed, file), os.path.join(compressed, file))


# call the function
observe_directory(uncompressed, compressed)

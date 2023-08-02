import os
import time

from dotenv import load_dotenv
from watchdog.observers import Observer

from file_handler import FileChangeHandler

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
# call the function
observe_directory(uncompressed, compressed)

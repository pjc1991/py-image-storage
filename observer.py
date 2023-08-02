import asyncio
import os

from dotenv import load_dotenv
from watchdog.observers import Observer

from file_handler import FileChangeHandler, handle_file

load_dotenv()


async def observe_directory(dir_path: str, new_dir_path: str) -> None:
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


async def initial_file_handle(file_path: str, new_file_path: str):
    print('--- searching for files ---')
    for root, dirs, files in os.walk(file_path):
        print(f'Files in {root}: {files}')
        for file in files:
            print(f'File: {file}')
            file_path = os.path.join(root, file)
            new_file_path = file_path.replace(file_path, new_file_path)
            await handle_file(file_path, new_file_path)
    print('--- finished searching for files ---')


uncompressed = os.getenv('UNCOMPRESSED')
compressed = os.getenv('COMPRESSED')

if __name__ == "__main__":
    # check all files in the directory before starting
    # initial file handling
    print(f'Checking files in {uncompressed}')
    print(f'Compressed files will be stored in {compressed}')
    asyncio.run(initial_file_handle(uncompressed, compressed))

    # start the observer
    print('--- starting observer ---')
    asyncio.run(observe_directory(uncompressed, compressed))

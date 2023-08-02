import asyncio
import os
from asyncio import Queue

from dotenv import load_dotenv
from watchdog.observers import Observer

from file_handler import FileChangeHandler, handle_file

load_dotenv()


async def observe_directory(dir_path: str, new_dir_path: str, queue: Queue) -> None:
    event_handler = FileChangeHandler(dir_path, new_dir_path, queue)
    observer = Observer()
    observer.schedule(event_handler, dir_path, recursive=True)
    observer.start()

    try:
        while True:
            if not queue.empty():
                file_path, new_file_path = queue.get_nowait()
                await handle_file(file_path, new_file_path)
            else:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


async def initial_file_handle(file_path: str, new_file_path: str, que: Queue):
    print('--- searching for files ---')
    for root, dirs, files in os.walk(file_path):
        print(f'Files in {root}: {files}')
        for file in files:
            print(f'File: {file}')
            file_path = os.path.join(root, file)
            new_file_path = file_path.replace(file_path, new_file_path)
            que.put_nowait((file_path, new_file_path))

    tasks = []
    while not que.empty():
        file_path, new_file_path = que.get_nowait()
        tasks.append(handle_file(file_path, new_file_path))
    await asyncio.gather(*tasks)
    print('--- finished searching for files ---')


uncompressed = os.getenv('UNCOMPRESSED')
compressed = os.getenv('COMPRESSED')

if __name__ == "__main__":
    queue = asyncio.Queue()

    # check all files in the directory before starting
    # initial file handling
    print(f'Checking files in {uncompressed}')
    print(f'Compressed files will be stored in {compressed}')
    asyncio.run(initial_file_handle(uncompressed, compressed, queue))

    # start the observer
    print('--- starting observer ---')
    asyncio.run(observe_directory(uncompressed, compressed, queue))

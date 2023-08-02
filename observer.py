import asyncio
import os
from asyncio import Queue
from datetime import datetime

from dotenv import load_dotenv
from watchdog.observers import Observer

from file_handler import FileChangeHandler, handle_file

load_dotenv()


async def observe_directory(dir_path: str, new_dir_path: str, queue_provided: Queue) -> None:
    event_handler = FileChangeHandler(dir_path, new_dir_path, queue_provided)
    observer = Observer()
    observer.schedule(event_handler, dir_path, recursive=True)
    observer.start()

    try:
        while True:
            if not queue_provided.empty():
                file_path, new_file_path = queue_provided.get_nowait()
                await handle_file(file_path, new_file_path)
            else:
                # run initialized every 10 minute
                if datetime.now().minute % 10 == 0 and datetime.now().second == 0:
                    initialize(queue_provided)
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


async def initial_file_handle(uncompressed_path: str, compressed_path: str, que: Queue):
    print('--- searching for files ---')
    for root, dirs, files in os.walk(uncompressed_path):
        print(f'Files in {root}: {files}')
        for file in files:
            print(f'File: {file}')
            file_path = os.path.join(root, file)
            # if the file_path is in the uncompressed root directory
            # add the YYYY-MM directory to the new file path
            # YYYY-MM is the month the file was modified
            if uncompressed_path == root:
                yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                print(f'File {file} is in the root directory')
                new_file_path = os.path.join(compressed_path, yyyy_mm, file)

            else:
                new_file_path = file_path.replace(uncompressed_path, compressed_path)
            print(f'File path: {file_path}')
            print(f'New file path: {new_file_path}')
            que.put_nowait((file_path, new_file_path))

    tasks = []
    while not que.empty():
        print('--- handling files ---')
        file_path, new_file_path = que.get_nowait()
        task = asyncio.create_task(handle_file(file_path, new_file_path))
        tasks.append(task)

    await asyncio.gather(*tasks)
    print('--- finished searching for files ---')


uncompressed = os.getenv('UNCOMPRESSED')
compressed = os.getenv('COMPRESSED')


def initialize(queue_provided: Queue = None):
    if queue_provided is None:
        raise ValueError('Queue must be provided')

    # check all files in the directory before starting
    # initial file handling
    print(f'Checking files in {uncompressed}')
    print(f'Compressed files will be stored in {compressed}')
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initial_file_handle(uncompressed, compressed, queue))


if __name__ == "__main__":
    queue = asyncio.Queue()
    initialize(queue)

    # start the observer
    print('--- starting observer ---')
    asyncio.run(observe_directory(uncompressed, compressed, queue))

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
    tasks = []
    try:
        while True:
            if not queue_provided.empty():
                await work_task_until_n(tasks, queue_provided)
                await asyncio.gather(*tasks)
            else:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


async def work_task_until_n(tasks, queue_provided, n=50):
    while not queue_provided.empty() and len(tasks) < n:
        if len(tasks) >= n:
            print('--- waiting for tasks to finish ---')
            await asyncio.gather(*tasks)
            tasks = []
        print('--- handling files ---')
        file_path, new_file_path = queue_provided.get_nowait()
        task = asyncio.create_task(handle_file(file_path, new_file_path))
        tasks.append(task)



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
            if uncompressed_path == root and os.path.isfile(file_path):
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
        await work_task_until_n(tasks, que)
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
    loop = asyncio.get_event_loop()
    loop.run_until_complete(initial_file_handle(uncompressed, compressed, queue))

    # start the observer
    print('--- starting observer ---')
    asyncio.run(observe_directory(uncompressed, compressed, queue))

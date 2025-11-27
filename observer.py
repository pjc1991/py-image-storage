import asyncio
import os
from asyncio import Queue
from datetime import datetime

from dotenv import load_dotenv
from watchdog.observers import Observer

import task_handler
from file_handler import FileChangeHandler

load_dotenv()


async def periodic_cleanup(dir_path: str, new_dir_path: str, queue: Queue):
    interval = int(os.getenv('CLEANUP_INTERVAL_SECONDS', 60))
    print(f'--- starting periodic cleanup every {interval} seconds ---')
    while True:
        await asyncio.sleep(interval)
        print('--- running periodic cleanup ---')
        
        # 1. Scan for remaining files (similar to initial_file_handle)
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = os.path.join(root, file)
                # Skip if file is currently being written to (simple check, handle_file does more)
                if not os.path.exists(file_path):
                    continue
                    
                if dir_path == root:
                    yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                    new_file_path = os.path.join(new_dir_path, yyyy_mm, file)
                else:
                    new_file_path = file_path.replace(dir_path, new_dir_path)
                
                # Add to queue if not already there (cache check handles duplicates in handler, 
                # but we can just add it and let handler decide)
                queue.put_nowait((file_path, new_file_path))

        # 2. Delete empty folders
        for root, dirs, files in os.walk(dir_path, topdown=False):
            if root == dir_path:
                continue
            if not os.listdir(root):
                try:
                    os.rmdir(root)
                    print(f'Removed empty directory: {root}')
                except OSError:
                    pass # Directory might not be empty or other error


async def observe_directory(dir_path: str, new_dir_path: str, queue_provided: Queue) -> None:
    event_handler = FileChangeHandler(dir_path, new_dir_path, queue_provided)
    observer = Observer()
    observer.schedule(event_handler, dir_path, recursive=True)
    observer.start()
    
    # Start periodic cleanup task
    cleanup_task = asyncio.create_task(periodic_cleanup(dir_path, new_dir_path, queue_provided))
    
    try:
        while True:
            if not queue_provided.empty():
                await task_handler.handle_tasks(queue_provided)
            else:
                await asyncio.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        cleanup_task.cancel()
    observer.join()


async def initial_file_handle(uncompressed_path: str, compressed_path: str, que: Queue):
    print('--- searching for files ---')
    for root, dirs, files in os.walk(uncompressed_path):
        print(f'Files in {root}: {files}')
        for file in files:
            print(f'File: {file}')
            file_path = os.path.join(root, file)
            if uncompressed_path == root and os.path.isfile(file_path):
                yyyy_mm = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m')
                print(f'File {file} is in the root directory')
                new_file_path = os.path.join(compressed_path, yyyy_mm, file)

            else:
                new_file_path = file_path.replace(uncompressed_path, compressed_path)
            print(f'File path: {file_path}')
            print(f'New file path: {new_file_path}')
            que.put_nowait((file_path, new_file_path))

    await task_handler.handle_tasks(que)

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
    loop.close()

    # start the observer
    print('--- starting observer ---')
    asyncio.run(observe_directory(uncompressed, compressed, queue))

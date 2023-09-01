import asyncio
import concurrent.futures
import enum
import multiprocessing
from asyncio import Queue

from aiomultiprocess import Pool

from file_handler import handle_file


class TaskHandleType(enum.Enum):
    asyncio = 'asyncio'
    bounded_semaphore = 'bounded_semaphore'
    multi_process = 'multi_process'
    aiomultiprocess = 'aiomultiprocess'
    process_pool_executor = 'process_pool_executor'


mode = TaskHandleType.asyncio


async def __handle_file_with_semaphore__(file_path: str, new_file_path: str, semaphore):
    async with semaphore:
        await handle_file(file_path, new_file_path)


async def __handle_tasks_semaphore__(queue: Queue):
    semaphore = asyncio.BoundedSemaphore(50)
    tasks = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        tasks.append(__handle_file_with_semaphore__(file_path, new_file_path, semaphore))

    await asyncio.gather(*tasks)


def __process_task__(file_path, new_file_path):
    asyncio.run(handle_file(file_path, new_file_path))


def __process_task__arg(args):
    file_path, new_file_path = args
    asyncio.run(handle_file(file_path, new_file_path))


def __handle_tasks_multi_process__(queue):
    tasks = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        tasks.append((file_path, new_file_path))

    with multiprocessing.Pool() as pool:
        pool.map(__process_task__, tasks)


async def __handle_task__(args):
    file_path, new_file_path = args
    await handle_file(file_path, new_file_path)


async def __handle_tasks_aiomultiprocess__(queue):
    tasks = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        tasks.append((file_path, new_file_path))

    async with Pool() as pool:
        await pool.map(__handle_task__, tasks)


async def __handle_tasks_process_pool_executor__(queue):
    file_paths = []
    new_file_paths = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        file_paths.append(file_path)
        new_file_paths.append(new_file_path)

    with concurrent.futures.ProcessPoolExecutor() as executor:
        results = executor.map(__process_task__, file_paths, new_file_paths)


async def __handle_tasks_asyncio__(queue):
    tasks = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        tasks.append(asyncio.create_task(handle_file(file_path, new_file_path)))

    await asyncio.gather(*tasks)


async def handle_tasks(queue: Queue):
    if mode == TaskHandleType.asyncio:
        await __handle_tasks_asyncio__(queue)
        return

    if mode == TaskHandleType.bounded_semaphore:
        await __handle_tasks_semaphore__(queue)
        return

    if mode == TaskHandleType.multi_process:
        __handle_tasks_multi_process__(queue)
        return

    if mode == TaskHandleType.aiomultiprocess:
        await __handle_tasks_aiomultiprocess__(queue)
        return

    if mode == TaskHandleType.process_pool_executor:
        await __handle_tasks_process_pool_executor__(queue)
        return

    raise Exception('Invalid mode')


if __name__ == "__main__":
    pass

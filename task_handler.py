import asyncio
import enum
from asyncio import Queue
from multiprocessing import Process

from aiomultiprocess import Pool

from file_handler import handle_file


class TaskHandleType(enum.Enum):
    bounded_semaphore = 'bounded_semaphore'
    multi_process = 'multi_process'
    aiomultiprocess = 'aiomultiprocess'


mode = TaskHandleType.aiomultiprocess


async def __handle_file_with_semaphore__(file_path: str, new_file_path: str, semaphore):
    async with semaphore:
        await handle_file(file_path, new_file_path)


async def __handle_tasks_semaphore__(queue: Queue):
    semaphore = asyncio.BoundedSemaphore(30)
    tasks = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        tasks.append(__handle_file_with_semaphore__(file_path, new_file_path, semaphore))

    await asyncio.gather(*tasks)


def __process_task__(file_path: str, new_file_path: str):
    asyncio.run(handle_file(file_path, new_file_path))


def __handle_tasks_multi_process__(queue):
    processes = []
    while not queue.empty():
        file_path, new_file_path = queue.get_nowait()
        process = Process(target=__process_task__, args=(file_path, new_file_path))
        process.start()
        processes.append(process)

    for process in processes:
        process.join()


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


async def handle_tasks(queue: Queue):
    if mode == TaskHandleType.bounded_semaphore:
        await __handle_tasks_semaphore__(queue)
        return

    if mode == TaskHandleType.multi_process:
        __handle_tasks_multi_process__(queue)
        return

    if mode == TaskHandleType.aiomultiprocess:
        await __handle_tasks_aiomultiprocess__(queue)
        return

    raise Exception('Invalid mode')


if __name__ == "__main__":
    pass

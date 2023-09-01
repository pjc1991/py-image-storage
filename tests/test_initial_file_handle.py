import asyncio
import os
import shutil
import time
import unittest

import observer
import task_handler


class TestInitialFileHandle(unittest.TestCase):
    def test_initial_file_handle(self):
        # given

        # current path
        current_path = os.getcwd()

        # original folder for dummy images
        original_folder = current_path + os.sep + os.sep + 'test_images' + os.sep + 'original'

        # uncompressed folder for storing the uncompressed images
        uncompressed_folder = current_path + os.sep + os.sep + 'test_images' + os.sep + 'uncompressed'

        # compressed folder for the result
        compressed_folder = current_path + os.sep + os.sep + 'test_images' + os.sep + 'compressed'

        # copy the files from tests/test_images/original to tests/test_images/uncompressed
        copy(original_folder, uncompressed_folder)

        # prepare the queue
        queue = asyncio.Queue()

        # when
        # measure the time it takes to run the initial_file_handle function

        start_time = time.perf_counter()
        asyncio.run(observer.initial_file_handle(uncompressed_folder, compressed_folder, que=queue))

        end_time = time.perf_counter()
        execution_time = end_time - start_time

        # then
        print(f'Execution time: {execution_time} seconds')
        pass

        # clean up
        # delete the files from tests/test_images/uncompressed
        for root, dirs, files in os.walk(uncompressed_folder):
            for file in files:
                os.remove(os.path.join(root, file))

        # delete the files from tests/test_images/compressed
        for root, dirs, files in os.walk(compressed_folder):
            for file in files:
                os.remove(os.path.join(root, file))

    def test_initial_file_handle_performance_test(self):
        # given

        # current path
        current_path = os.getcwd()

        # original folder for dummy images
        original_folder = current_path + os.sep + 'test_images' + os.sep + 'original'

        # uncompressed folder for storing the uncompressed images
        uncompressed_folder = current_path + os.sep + 'test_images' + os.sep + 'uncompressed'

        # compressed folder for the result
        compressed_folder = current_path + os.sep + 'test_images' + os.sep + 'compressed'

        # copy the files from tests/test_images/original to tests/test_images/uncompressed
        copy(original_folder, uncompressed_folder)

        # prepare the queue
        queue = asyncio.Queue()

        # when
        # measure the time it takes to run the initial_file_handle function
        aio_execution_time = task_handle(task_handler.TaskHandleType.aiomultiprocess, queue, uncompressed_folder, compressed_folder)

        # change the mode to multi-process
        copy(original_folder, uncompressed_folder)
        mp_execution_time = task_handle(task_handler.TaskHandleType.multi_process, queue, uncompressed_folder, compressed_folder)

        # change the mode to bounded semaphore
        copy(original_folder, uncompressed_folder)
        bs_execution_time = task_handle(task_handler.TaskHandleType.bounded_semaphore, queue, uncompressed_folder, compressed_folder)

        # then
        print(f'Execution time for aiomultiprocess: {aio_execution_time} seconds')
        print(f'Execution time for multi process: {mp_execution_time} seconds')
        print(f'Execution time for bounded semaphore: {bs_execution_time} seconds')
        pass


def task_handle(mode: task_handler.TaskHandleType, queue: asyncio.Queue, uncompressed_folder: str,
                compressed_folder: str):
    task_handler.mode = mode
    start_time = time.perf_counter()

    asyncio.run(observer.initial_file_handle(uncompressed_folder, compressed_folder, que=queue))

    end_time = time.perf_counter()
    execution_time = end_time - start_time
    clean_up([uncompressed_folder, compressed_folder])

    return execution_time


def clean_up(dirs):
    for dir in dirs:
        for root, dirs, files in os.walk(dir):
            for file in files:
                os.remove(os.path.join(root, file))


def copy(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True)


if __name__ == '__main__':
    unittest.main()

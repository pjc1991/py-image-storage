import asyncio
import os
import time
import unittest
from distutils.dir_util import copy_tree

import observer


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
        copy_tree(original_folder, uncompressed_folder)

        # prepare the queue
        queue = asyncio.Queue()

        # when
        # measure the time it takes to run the initial_file_handle function

        start_time = time.perf_counter()

        loop = asyncio.get_event_loop()
        loop.run_until_complete(observer.initial_file_handle(uncompressed_folder, compressed_folder, que=queue))
        loop.close()

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


if __name__ == '__main__':
    unittest.main()

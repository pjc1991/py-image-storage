import asyncio
import os
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
        loop = asyncio.get_event_loop()
        loop.run_until_complete(observer.initial_file_handle('tests/uncompressed', 'tests/compressed', que=queue))
        loop.close()

        # then
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

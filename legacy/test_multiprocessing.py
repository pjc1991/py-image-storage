import unittest
import asyncio
import os
import tempfile
from unittest.mock import patch, MagicMock
from task_handler import __process_task__, TaskHandleType, mode
import task_handler


class TestHandleFileMultiprocessing(unittest.TestCase):
    def test_process_task_function(self):
        """Test the __process_task__ function that's used in multiprocessing"""
        file_path = "test_image.png"
        new_file_path = "compressed/test_image.png"
        
        # Mocking to avoid actual file operations
        with patch('os.path.exists') as mock_exists, \
             patch('os.path.getsize') as mock_getsize, \
             patch('os.makedirs') as mock_makedirs, \
             patch('os.rename') as mock_rename, \
             patch('file_handler.wait_for_file_ready') as mock_wait, \
             patch('file_handler.async_compress_image') as mock_compress:
            
            # Configure mocks
            mock_exists.return_value = True
            
            async def async_true(*args, **kwargs):
                return True
            mock_wait.side_effect = async_true
            mock_getsize.return_value = 2048 * 1024  # 2MB
            
            # This should trigger the NameError if asyncio is not properly available
            try:
                __process_task__(file_path, new_file_path)
            except NameError as e:
                if 'asyncio' in str(e):
                    self.fail(f"NameError with asyncio: {e}")
                else:
                    raise
            except Exception as e:
                # Other exceptions are okay for this test
                print(f"Got expected exception: {e}")
                pass

    def test_multiprocess_mode(self):
        """Test running in actual multiprocess mode"""
        queue = asyncio.Queue()
        
        # Add a test task
        file_path = os.path.join(tempfile.gettempdir(), "test_image.png")
        new_file_path = os.path.join(tempfile.gettempdir(), "compressed", "test_image.png")
        
        # Create a dummy file
        with open(file_path, 'wb') as f:
            f.write(b'fake image data')
        
        queue.put_nowait((file_path, new_file_path))
        
        # Set mode to multiprocess
        original_mode = task_handler.mode
        task_handler.mode = TaskHandleType.multi_process
        
        try:
            with patch('file_handler.async_compress_image'):
                # This will actually spawn processes
                task_handler.__handle_tasks_multi_process__(queue)
        except NameError as e:
            if 'asyncio' in str(e):
                self.fail(f"NameError with asyncio in multiprocess mode: {e}")
            else:
                raise
        finally:
            task_handler.mode = original_mode
            # Cleanup
            if os.path.exists(file_path):
                os.remove(file_path)


if __name__ == '__main__':
    unittest.main()

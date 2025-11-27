import unittest
import asyncio
import os
import tempfile
import shutil
from datetime import datetime
import task_handler
from task_handler import TaskHandleType


class TestMultiprocessingAsyncio(unittest.TestCase):
    """Test that multiprocessing worker functions can properly import and use asyncio"""
    
    def setUp(self):
        """Create temporary directories for testing"""
        self.test_dir = tempfile.mkdtemp()
        self.source_dir = os.path.join(self.test_dir, 'source')
        self.dest_dir = os.path.join(self.test_dir, 'dest')
        os.makedirs(self.source_dir)
        os.makedirs(self.dest_dir)
        
    def tearDown(self):
        """Clean up temporary directories"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def test_process_task_arg_with_psd_file(self):
        """Test that __process_task__arg can handle .psd files without asyncio NameError"""
        # Create a test .psd file (just a dummy file for testing)
        test_file = os.path.join(self.source_dir, 'test.psd')
        with open(test_file, 'wb') as f:
            f.write(b'dummy psd content')

        # Set up destination path
        dest_file = os.path.join(self.dest_dir, 'test.psd')

        # This should not raise a NameError about asyncio
        try:
            # Use getattr to bypass Python's name mangling
            process_task_arg = getattr(task_handler, '__process_task__arg')
            process_task_arg((test_file, dest_file))
            # Verify the file was moved
            self.assertTrue(os.path.exists(dest_file), "File should be moved to destination")
            self.assertFalse(os.path.exists(test_file), "Source file should be removed after move")
        except NameError as e:
            self.fail(f"NameError raised: {e}. The asyncio import fix did not work.")
    
    def test_multiprocessing_mode_with_queue(self):
        """Test the full multiprocessing pipeline with a queue of .psd files"""
        # Save the current mode
        original_mode = task_handler.mode
        
        try:
            # Set to multiprocessing mode
            task_handler.mode = TaskHandleType.multi_process
            
            # Create multiple test .psd files
            test_files = []
            for i in range(3):
                test_file = os.path.join(self.source_dir, f'test_{i}.psd')
                with open(test_file, 'wb') as f:
                    f.write(b'dummy psd content ' * 100)  # Make it a bit larger
                test_files.append(test_file)
            
            # Create a queue with file tasks
            queue = asyncio.Queue()
            for test_file in test_files:
                dest_file = os.path.join(self.dest_dir, os.path.basename(test_file))
                queue.put_nowait((test_file, dest_file))
            
            # Run the task handler (this uses multiprocessing internally)
            # We need to run this in an async context
            async def run_test():
                await task_handler.handle_tasks(queue)
            
            # Execute the async function
            asyncio.run(run_test())
            
            # Verify all files were processed
            for test_file in test_files:
                dest_file = os.path.join(self.dest_dir, os.path.basename(test_file))
                self.assertTrue(os.path.exists(dest_file), 
                              f"File {dest_file} should exist after processing")
                
        except NameError as e:
            self.fail(f"NameError raised during multiprocessing: {e}")
        finally:
            # Restore original mode
            task_handler.mode = original_mode


if __name__ == '__main__':
    unittest.main()

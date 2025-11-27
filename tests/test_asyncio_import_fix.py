"""
Simple test to verify that the asyncio import fix works in multiprocessing context.
This test directly calls the worker function that was causing the NameError.
"""
import multiprocessing
import os
import tempfile
import sys

# Add parent directory to path so we can import task_handler
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_process_task_arg_simple():
    """Test that __process_task__arg can be called without NameError"""
    # Import here to avoid dependency issues
    from task_handler import __process_task__arg
    
    # Create temporary files
    with tempfile.TemporaryDirectory() as tmpdir:
        source_file = os.path.join(tmpdir, 'test.psd')
        dest_file = os.path.join(tmpdir, 'dest', 'test.psd')
        
        # Create source file
        with open(source_file, 'wb') as f:
            f.write(b'dummy psd content')
        
        # Create dest directory
        os.makedirs(os.path.dirname(dest_file), exist_ok=True)
        
        # This should not raise NameError: name 'asyncio' is not defined
        try:
            __process_task__arg((source_file, dest_file))
            print("✓ Test passed: No NameError occurred")
            print(f"✓ File moved successfully: {os.path.exists(dest_file)}")
            return True
        except NameError as e:
            print(f"✗ Test failed: NameError occurred: {e}")
            return False
        except Exception as e:
            print(f"✓ Test passed: No NameError (other error is expected): {type(e).__name__}: {e}")
            # Other errors are OK - we're just testing that asyncio is imported
            return True


def test_with_multiprocessing_pool():
    """Test using actual multiprocessing.Pool to ensure it works in worker processes"""
    from task_handler import __process_task__arg
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create multiple test files
        tasks = []
        for i in range(3):
            source_file = os.path.join(tmpdir, f'test_{i}.psd')
            dest_file = os.path.join(tmpdir, 'dest', f'test_{i}.psd')
            
            with open(source_file, 'wb') as f:
                f.write(b'dummy psd content ' * 100)
            
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            tasks.append((source_file, dest_file))
        
        # Run with multiprocessing pool
        try:
            with multiprocessing.Pool(processes=2) as pool:
                pool.map(__process_task__arg, tasks)
            print("✓ Multiprocessing test passed: No NameError in worker processes")
            return True
        except NameError as e:
            print(f"✗ Multiprocessing test failed: NameError in worker: {e}")
            return False
        except Exception as e:
            print(f"✓ Multiprocessing test passed: No NameError (other error is expected): {type(e).__name__}")
            return True


if __name__ == '__main__':
    print("Testing asyncio import fix in multiprocessing context...\n")
    
    print("Test 1: Direct function call")
    result1 = test_process_task_arg_simple()
    
    print("\nTest 2: Multiprocessing pool")
    result2 = test_with_multiprocessing_pool()
    
    print("\n" + "="*50)
    if result1 and result2:
        print("All tests passed! ✓")
        sys.exit(0)
    else:
        print("Some tests failed! ✗")
        sys.exit(1)

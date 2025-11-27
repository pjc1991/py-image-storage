"""
Tests for file processing functionality.
"""
import os
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from PIL import Image

from processor import FileProcessor
from compressor import ImageCompressor
from config import Config


class TestFileProcessor:
    """Test FileProcessor class"""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration"""
        uncompressed = tmp_path / 'uncompressed'
        compressed = tmp_path / 'compressed'
        uncompressed.mkdir()
        compressed.mkdir()

        config = Mock(spec=Config)
        config.uncompressed_path = str(uncompressed)
        config.compressed_path = str(compressed)
        config.min_file_size_kb = 10  # Small threshold for testing
        return config

    @pytest.fixture
    def mock_compressor(self):
        """Create mock compressor"""
        compressor = Mock(spec=ImageCompressor)
        compressor.should_compress = Mock(return_value=True)
        compressor.compress = AsyncMock(return_value=True)
        return compressor

    @pytest.fixture
    def processor(self, config, mock_compressor):
        """Create FileProcessor instance"""
        return FileProcessor(config, mock_compressor)

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test image file"""
        image_path = tmp_path / 'test.jpg'
        img = Image.new('RGB', (100, 100), color='red')
        img.save(str(image_path), 'JPEG')
        return image_path

    @pytest.mark.asyncio
    async def test_wait_for_file_ready_success(self, processor, test_image):
        """Test waiting for file to be ready"""
        result = await processor.wait_for_file_ready(str(test_image), timeout=2)
        assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_file_ready_nonexistent(self, processor):
        """Test waiting for non-existent file"""
        result = await processor.wait_for_file_ready('/nonexistent/file.jpg', timeout=1)
        assert result is False

    @pytest.mark.asyncio
    async def test_process_file_compress(self, processor, mock_compressor, test_image, tmp_path):
        """Test processing file that needs compression"""
        dest_path = tmp_path / 'output' / 'test.jpg'

        # Configure mock
        mock_compressor.should_compress.return_value = True

        result = await processor.process_file(str(test_image), str(dest_path))

        assert result is True
        assert not test_image.exists()  # Original should be removed
        mock_compressor.compress.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_file_move_only(self, processor, mock_compressor, test_image, tmp_path):
        """Test processing file that doesn't need compression"""
        dest_path = tmp_path / 'output' / 'test.jpg'

        # Configure mock to not compress
        mock_compressor.should_compress.return_value = False

        result = await processor.process_file(str(test_image), str(dest_path))

        assert result is True
        assert dest_path.exists()
        assert not test_image.exists()
        mock_compressor.compress.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_file_nonexistent(self, processor):
        """Test processing non-existent file"""
        result = await processor.process_file('/nonexistent.jpg', '/output.jpg')
        assert result is False

    @pytest.mark.asyncio
    async def test_process_file_directory(self, processor, tmp_path):
        """Test that directories are skipped"""
        dir_path = tmp_path / 'testdir'
        dir_path.mkdir()

        result = await processor.process_file(str(dir_path), '/output')
        assert result is False

    @pytest.mark.asyncio
    async def test_process_file_webp(self, processor, tmp_path):
        """Test processing WebP file (should just move)"""
        webp_file = tmp_path / 'test.webp'
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(str(webp_file), 'WEBP')

        dest_path = tmp_path / 'output' / 'test.webp'

        result = await processor.process_file(str(webp_file), str(dest_path))

        assert result is True
        assert dest_path.exists()
        assert not webp_file.exists()

    @pytest.mark.asyncio
    async def test_process_batch(self, processor, tmp_path, mock_compressor):
        """Test batch processing multiple files"""
        # Create multiple test files
        files = []
        for i in range(3):
            file_path = tmp_path / f'test{i}.txt'
            file_path.write_text(f'test {i}')
            dest_path = tmp_path / 'output' / f'test{i}.txt'
            files.append((str(file_path), str(dest_path)))

        mock_compressor.should_compress.return_value = False

        result = await processor.process_batch(files)

        assert result['success'] == 3
        assert result['failed'] == 0

    @pytest.mark.asyncio
    async def test_process_batch_empty(self, processor):
        """Test batch processing with empty list"""
        result = await processor.process_batch([])

        assert result['success'] == 0
        assert result['failed'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

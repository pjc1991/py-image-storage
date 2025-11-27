"""
Tests for image compression functionality.
"""
import os
import pytest
import asyncio
from pathlib import Path
from PIL import Image
from unittest.mock import Mock

from compressor import ImageCompressor
from config import Config


class TestImageCompressor:
    """Test ImageCompressor class"""

    @pytest.fixture
    def config(self, tmp_path):
        """Create test configuration"""
        config = Mock(spec=Config)
        config.uncompressed_path = str(tmp_path / 'uncompressed')
        config.compressed_path = str(tmp_path / 'compressed')
        config.max_resolution = 1920
        config.compression_quality = 85
        config.min_file_size_kb = 1  # Very small threshold for testing
        config.cache_maxsize = 10
        config.cache_ttl = 60
        return config

    @pytest.fixture
    def compressor(self, config):
        """Create ImageCompressor instance"""
        return ImageCompressor(config)

    @pytest.fixture
    def test_image(self, tmp_path):
        """Create a test JPEG image (large enough to compress)"""
        image_path = tmp_path / 'test_image.jpg'

        # Create a larger test image to exceed min_file_size_kb threshold
        img = Image.new('RGB', (1920, 1080), color='red')
        img.save(str(image_path), 'JPEG', quality=95)

        return str(image_path)

    def test_compressor_initialization(self, config):
        """Test compressor initializes correctly"""
        compressor = ImageCompressor(config)

        assert compressor.config == config
        assert compressor.cache is not None
        assert compressor.cache.maxsize == 10
        assert compressor.cache.ttl == 60

    def test_should_compress_jpeg(self, compressor, test_image):
        """Test should compress JPEG images"""
        assert compressor.should_compress(test_image) is True

    def test_should_compress_png(self, compressor, tmp_path):
        """Test should compress PNG images"""
        png_path = tmp_path / 'test.png'
        # Make image large enough to exceed threshold
        img = Image.new('RGB', (1920, 1080), color='blue')
        img.save(str(png_path), 'PNG')

        assert compressor.should_compress(str(png_path)) is True

    def test_should_not_compress_webp(self, compressor, tmp_path):
        """Test should not compress WebP images"""
        webp_path = tmp_path / 'test.webp'
        webp_path.write_text('fake webp')

        assert compressor.should_compress(str(webp_path)) is False

    def test_should_not_compress_non_image(self, compressor, tmp_path):
        """Test should not compress non-image files"""
        txt_path = tmp_path / 'test.txt'
        txt_path.write_text('hello')

        assert compressor.should_compress(str(txt_path)) is False

    def test_should_not_compress_small_file(self, compressor, tmp_path):
        """Test should not compress files below size threshold"""
        small_image = tmp_path / 'small.jpg'
        img = Image.new('RGB', (10, 10), color='green')
        img.save(str(small_image), 'JPEG')

        # File should be smaller than min_file_size_kb (100KB)
        assert compressor.should_compress(str(small_image)) is False

    @pytest.mark.asyncio
    async def test_compress_jpeg_to_webp(self, compressor, test_image, tmp_path):
        """Test compressing JPEG to WebP"""
        dest_path = tmp_path / 'output.webp'

        result = await compressor.compress(str(test_image), str(dest_path))

        assert result is True
        assert dest_path.exists()
        assert dest_path.suffix == '.webp'

        # Verify it's a valid WebP image
        with Image.open(str(dest_path)) as img:
            assert img.format == 'WEBP'

    @pytest.mark.asyncio
    async def test_compress_caching(self, compressor, test_image, tmp_path):
        """Test that compression is cached"""
        dest_path = tmp_path / 'output.webp'

        # First compression
        result1 = await compressor.compress(str(test_image), str(dest_path))
        assert result1 is True

        # Second compression should be cached
        result2 = await compressor.compress(str(test_image), str(dest_path))
        assert result2 is True

        # Should only create one output file
        assert dest_path.exists()

    @pytest.mark.asyncio
    async def test_compress_large_image_resized(self, compressor, tmp_path):
        """Test that large images are resized"""
        # Create large image
        large_image = tmp_path / 'large.jpg'
        img = Image.new('RGB', (3840, 2160), color='yellow')  # 4K resolution
        img.save(str(large_image), 'JPEG')

        dest_path = tmp_path / 'output.webp'
        result = await compressor.compress(str(large_image), str(dest_path))

        assert result is True

        # Check resized dimensions
        with Image.open(str(dest_path)) as output_img:
            assert output_img.width <= compressor.config.max_resolution
            assert output_img.height <= compressor.config.max_resolution

    def test_ensure_webp_extension(self, compressor):
        """Test WebP extension handling"""
        assert compressor._ensure_webp_extension('test.jpg') == 'test.webp'
        assert compressor._ensure_webp_extension('test.png') == 'test.webp'
        assert compressor._ensure_webp_extension('test.webp') == 'test.webp'
        assert compressor._ensure_webp_extension('path/to/file.jpeg') == 'path/to/file.webp'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

"""
Tests for configuration management.
"""
import os
import pytest
import tempfile
from config import Config, ConfigurationError


class TestConfig:
    """Test Config class"""

    def test_config_from_env_with_valid_values(self, monkeypatch, tmp_path):
        """Test loading valid configuration from environment"""
        # Setup environment variables
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'uncompressed'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))
        monkeypatch.setenv('MIN_FILE_SIZE_KB', '512')
        monkeypatch.setenv('MAX_RESOLUTION', '1080')
        monkeypatch.setenv('COMPRESSION_QUALITY', '85')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')

        # Create directories
        (tmp_path / 'uncompressed').mkdir()
        (tmp_path / 'compressed').mkdir()

        # Load config
        config = Config.from_env()

        # Assertions
        assert config.uncompressed_path == str(tmp_path / 'uncompressed')
        assert config.compressed_path == str(tmp_path / 'compressed')
        assert config.min_file_size_kb == 512
        assert config.max_resolution == 1080
        assert config.compression_quality == 85
        assert config.log_level == 'DEBUG'

    def test_config_from_env_with_defaults(self, monkeypatch, tmp_path):
        """Test configuration with default values"""
        # Setup minimal environment
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'uncompressed'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))

        # Create directories
        (tmp_path / 'uncompressed').mkdir()
        (tmp_path / 'compressed').mkdir()

        # Load config
        config = Config.from_env()

        # Check defaults
        assert config.cleanup_interval_seconds == 60
        assert config.min_file_size_kb == 1024
        assert config.max_resolution == 1920
        assert config.compression_quality == 90
        assert config.log_level == 'INFO'

    def test_config_missing_required_variable(self, monkeypatch):
        """Test that missing required variables raise error"""
        # Only set one required variable
        monkeypatch.setenv('UNCOMPRESSED', '/some/path')

        # Should raise ConfigurationError
        with pytest.raises(ConfigurationError, match="Missing required environment variable"):
            Config.from_env()

    def test_config_invalid_integer_value(self, monkeypatch, tmp_path):
        """Test that invalid integer values raise error"""
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'uncompressed'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))
        monkeypatch.setenv('MIN_FILE_SIZE_KB', 'not_a_number')

        with pytest.raises(ConfigurationError, match="Invalid value"):
            Config.from_env()

    def test_config_validate_paths_exist(self, tmp_path, monkeypatch):
        """Test path validation"""
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'uncompressed'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))

        # Create directories
        (tmp_path / 'uncompressed').mkdir()
        (tmp_path / 'compressed').mkdir()

        config = Config.from_env()
        config.validate()  # Should not raise

    def test_config_validate_path_not_exist(self, tmp_path, monkeypatch):
        """Test validation fails for non-existent paths"""
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'nonexistent'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))

        config = Config.from_env()

        with pytest.raises(ConfigurationError, match="does not exist"):
            config.validate()

    def test_config_validate_invalid_quality(self, tmp_path, monkeypatch):
        """Test validation fails for invalid quality values"""
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'uncompressed'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))
        monkeypatch.setenv('COMPRESSION_QUALITY', '150')  # Invalid

        (tmp_path / 'uncompressed').mkdir()
        (tmp_path / 'compressed').mkdir()

        config = Config.from_env()

        with pytest.raises(ConfigurationError, match="compression_quality"):
            config.validate()

    def test_config_validate_invalid_log_level(self, tmp_path, monkeypatch):
        """Test validation fails for invalid log levels"""
        monkeypatch.setenv('UNCOMPRESSED', str(tmp_path / 'uncompressed'))
        monkeypatch.setenv('COMPRESSED', str(tmp_path / 'compressed'))
        monkeypatch.setenv('LOG_LEVEL', 'INVALID')

        (tmp_path / 'uncompressed').mkdir()
        (tmp_path / 'compressed').mkdir()

        config = Config.from_env()

        with pytest.raises(ConfigurationError, match="log_level"):
            config.validate()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

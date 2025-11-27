"""
Configuration management for the image storage service.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or incomplete."""
    pass


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    uncompressed_path: str
    compressed_path: str
    cleanup_interval_seconds: int = 60
    min_file_size_kb: int = 1024
    max_resolution: int = 1920
    compression_quality: int = 90
    cache_maxsize: int = 100
    cache_ttl: int = 60
    log_level: str = 'INFO'

    # Performance settings
    max_concurrent_compressions: int = 4  # Limit concurrent compressions
    skip_existing_files: bool = True  # Skip files that already exist at destination

    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'Config':
        """
        Load configuration from environment variables.

        Args:
            env_file: Optional path to .env file. If None, uses default .env

        Returns:
            Config instance

        Raises:
            ConfigurationError: If required variables are missing or invalid
        """
        load_dotenv(env_file)

        try:
            # Required variables
            uncompressed = os.environ['UNCOMPRESSED']
            compressed = os.environ['COMPRESSED']

            # Optional variables with defaults
            config = cls(
                uncompressed_path=uncompressed,
                compressed_path=compressed,
                cleanup_interval_seconds=cls._get_int('CLEANUP_INTERVAL_SECONDS', 60),
                min_file_size_kb=cls._get_int('MIN_FILE_SIZE_KB', 1024),
                max_resolution=cls._get_int('MAX_RESOLUTION', 1920),
                compression_quality=cls._get_int('COMPRESSION_QUALITY', 90),
                cache_maxsize=cls._get_int('CACHE_MAXSIZE', 100),
                cache_ttl=cls._get_int('CACHE_TTL', 60),
                log_level=os.getenv('LOG_LEVEL', 'INFO').upper(),
                max_concurrent_compressions=cls._get_int('MAX_CONCURRENT_COMPRESSIONS', 4),
                skip_existing_files=os.getenv('SKIP_EXISTING_FILES', 'true').lower() == 'true'
            )

            return config

        except KeyError as e:
            raise ConfigurationError(
                f"Missing required environment variable: {e}. "
                f"Please check your .env file."
            )

    @staticmethod
    def _get_int(key: str, default: int) -> int:
        """
        Get an integer environment variable with validation.

        Args:
            key: Environment variable name
            default: Default value if not set

        Returns:
            Integer value

        Raises:
            ConfigurationError: If value cannot be converted to int
        """
        value = os.getenv(key)
        if value is None:
            return default

        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(
                f"Invalid value for {key}: '{value}'. Must be an integer."
            )

    def validate(self) -> None:
        """
        Validate configuration values.

        Raises:
            ConfigurationError: If configuration is invalid
        """
        # Validate paths exist
        if not os.path.exists(self.uncompressed_path):
            raise ConfigurationError(
                f"Uncompressed path does not exist: {self.uncompressed_path}"
            )

        if not os.path.exists(self.compressed_path):
            raise ConfigurationError(
                f"Compressed path does not exist: {self.compressed_path}"
            )

        # Validate numeric ranges
        if self.cleanup_interval_seconds <= 0:
            raise ConfigurationError(
                f"cleanup_interval_seconds must be positive, got: {self.cleanup_interval_seconds}"
            )

        if self.min_file_size_kb < 0:
            raise ConfigurationError(
                f"min_file_size_kb must be non-negative, got: {self.min_file_size_kb}"
            )

        if not (0 < self.compression_quality <= 100):
            raise ConfigurationError(
                f"compression_quality must be between 1 and 100, got: {self.compression_quality}"
            )

        if self.max_resolution <= 0:
            raise ConfigurationError(
                f"max_resolution must be positive, got: {self.max_resolution}"
            )

        # Validate log level
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_levels:
            raise ConfigurationError(
                f"log_level must be one of {valid_levels}, got: {self.log_level}"
            )

        # Validate performance settings
        if self.max_concurrent_compressions <= 0:
            raise ConfigurationError(
                f"max_concurrent_compressions must be positive, got: {self.max_concurrent_compressions}"
            )

    def __str__(self) -> str:
        """Return a string representation (safe for logging)."""
        return (
            f"Config("
            f"uncompressed={self.uncompressed_path}, "
            f"compressed={self.compressed_path}, "
            f"cleanup_interval={self.cleanup_interval_seconds}s, "
            f"min_file_size={self.min_file_size_kb}KB, "
            f"max_resolution={self.max_resolution}px, "
            f"quality={self.compression_quality}%, "
            f"log_level={self.log_level}"
            f")"
        )

"""
Application orchestrator.
Coordinates all components and manages the application lifecycle.
"""
import asyncio
import signal
from typing import Optional

from config import Config, ConfigurationError
from compressor import ImageCompressor
from logger import setup_logging, get_logger
from processor import FileProcessor
from watcher import FileWatcher

logger = get_logger(__name__)


class Application:
    """
    Main application class that orchestrates all components.

    Responsibilities:
    - Initialize all components
    - Manage application lifecycle (startup, shutdown)
    - Handle graceful shutdown on signals
    - Coordinate between components
    """

    def __init__(self, config: Config):
        """
        Initialize the application.

        Args:
            config: Application configuration
        """
        self.config = config
        self.compressor: Optional[ImageCompressor] = None
        self.processor: Optional[FileProcessor] = None
        self.watcher: Optional[FileWatcher] = None
        self._shutdown_event = asyncio.Event()

        logger.debug('Application instance created')

    def _setup_components(self) -> None:
        """
        Initialize all application components with dependency injection.
        """
        logger.info('Initializing components...')

        # Create image compressor
        self.compressor = ImageCompressor(self.config)

        # Create file processor (depends on compressor)
        self.processor = FileProcessor(self.config, self.compressor)

        # Create file watcher (depends on processor)
        self.watcher = FileWatcher(self.config, self.processor)

        logger.info('All components initialized')

    def _setup_signal_handlers(self) -> None:
        """
        Setup signal handlers for graceful shutdown.
        """
        def signal_handler(sig, frame):
            logger.info(f'Received signal {sig}, initiating shutdown...')
            self._shutdown_event.set()

        try:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)
            logger.debug('Signal handlers registered')
        except ValueError:
            # Not in main thread, can't register signal handlers
            logger.debug('Could not register signal handlers (not in main thread)')

    async def startup(self) -> None:
        """
        Start the application and all its components.
        """
        logger.info('='*60)
        logger.info('Image Storage Service Starting')
        logger.info('='*60)
        logger.info(f'Configuration: {self.config}')
        logger.info(f'Source: {self.config.uncompressed_path}')
        logger.info(f'Destination: {self.config.compressed_path}')
        logger.info(f'Compression quality: {self.config.compression_quality}%')
        logger.info(f'Max resolution: {self.config.max_resolution}px')
        logger.info(f'Min file size: {self.config.min_file_size_kb}KB')

        # Log performance settings
        import os
        import multiprocessing
        cpu_count = multiprocessing.cpu_count()
        if os.getenv('MAX_CONCURRENT_COMPRESSIONS') is None:
            logger.info(f'Max concurrent compressions: {self.config.max_concurrent_compressions} (auto-detected from {cpu_count} CPU cores)')
        else:
            logger.info(f'Max concurrent compressions: {self.config.max_concurrent_compressions} (manually configured)')
        logger.info(f'Skip existing files: {self.config.skip_existing_files}')
        logger.info('='*60)

        # Setup components
        self._setup_components()

        # Setup signal handlers
        self._setup_signal_handlers()

        # Scan for initial files
        file_count = await self.watcher.scan_initial_files()

        # Process initial files
        if file_count > 0:
            logger.info(f'Processing {file_count} initial files...')
            await self.watcher.process_queue()
            logger.info('Initial file processing complete')
        else:
            logger.info('No initial files to process')

        logger.info('Application startup complete')
        logger.info('Monitoring for file changes...')

    async def run(self) -> None:
        """
        Run the main application loop.
        """
        try:
            # Start the watcher (this runs until cancelled)
            watcher_task = asyncio.create_task(self.watcher.start())

            # Wait for shutdown signal
            await self._shutdown_event.wait()

            # Cancel watcher
            watcher_task.cancel()
            try:
                await watcher_task
            except asyncio.CancelledError:
                pass

        except asyncio.CancelledError:
            logger.info('Application cancelled')
        except Exception as e:
            logger.error(f'Unexpected error in main loop: {e}', exc_info=True)
            raise

    async def shutdown(self) -> None:
        """
        Shutdown the application gracefully.
        """
        logger.info('='*60)
        logger.info('Shutting down Image Storage Service')
        logger.info('='*60)

        try:
            # Stop watcher
            if self.watcher:
                await self.watcher.stop()

            # Process any remaining queued files
            if self.watcher and not self.watcher.queue.empty():
                remaining = self.watcher.queue.qsize()
                logger.info(f'Processing {remaining} remaining files...')
                await self.watcher.process_queue()

            logger.info('Shutdown complete')
            logger.info('='*60)

        except Exception as e:
            logger.error(f'Error during shutdown: {e}', exc_info=True)

    async def run_async(self) -> None:
        """
        Complete async lifecycle: startup -> run -> shutdown.
        """
        try:
            await self.startup()
            await self.run()
        finally:
            await self.shutdown()


def create_app() -> Application:
    """
    Factory function to create and configure the application.

    Returns:
        Configured Application instance

    Raises:
        ConfigurationError: If configuration is invalid
    """
    # Load configuration
    config = Config.from_env()

    # Setup logging
    setup_logging(config.log_level)

    # Validate configuration
    config.validate()

    # Create application
    app = Application(config)

    return app


async def main() -> None:
    """
    Main entry point for the application.
    """
    try:
        # Create application
        app = create_app()

        # Run application
        await app.run_async()

    except ConfigurationError as e:
        print(f'Configuration error: {e}')
        print('Please check your .env file and ensure all required variables are set.')
        return

    except KeyboardInterrupt:
        logger.info('Keyboard interrupt received')

    except Exception as e:
        logger.error(f'Fatal error: {e}', exc_info=True)
        raise


if __name__ == '__main__':
    # Run the application
    asyncio.run(main())

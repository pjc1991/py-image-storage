#!/usr/bin/env python3
"""
Performance benchmark script for Image Storage Service.

This script tests different concurrency settings and measures:
- Throughput (files/second)
- CPU usage
- Memory usage
- Total processing time

Usage:
    python benchmark.py [--test-files N] [--min-workers 1] [--max-workers 16]
"""
import argparse
import asyncio
import multiprocessing
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Tuple

try:
    from PIL import Image
    import psutil
except ImportError:
    print("Error: Required packages not installed")
    print("Run: pip install Pillow psutil")
    sys.exit(1)

from config import Config
from compressor import ImageCompressor
from processor import FileProcessor


class BenchmarkResult:
    """Results from a benchmark run."""

    def __init__(
        self,
        workers: int,
        total_time: float,
        files_processed: int,
        avg_cpu_percent: float,
        peak_memory_mb: float
    ):
        self.workers = workers
        self.total_time = total_time
        self.files_processed = files_processed
        self.throughput = files_processed / total_time if total_time > 0 else 0
        self.avg_cpu_percent = avg_cpu_percent
        self.peak_memory_mb = peak_memory_mb

    def __str__(self) -> str:
        return (
            f"Workers: {self.workers:2d} | "
            f"Time: {self.total_time:6.2f}s | "
            f"Throughput: {self.throughput:5.2f} files/s | "
            f"CPU: {self.avg_cpu_percent:5.1f}% | "
            f"Memory: {self.peak_memory_mb:6.1f}MB"
        )


def create_test_images(count: int, directory: Path) -> List[Path]:
    """
    Create test images for benchmarking.

    Args:
        count: Number of images to create
        directory: Directory to create images in

    Returns:
        List of created image paths
    """
    print(f"Creating {count} test images...")
    images = []

    for i in range(count):
        # Create varied image sizes for realistic testing
        if i % 3 == 0:
            size = (1920, 1080)  # Full HD
        elif i % 3 == 1:
            size = (1280, 720)   # HD
        else:
            size = (800, 600)    # Small

        # Vary formats
        if i % 2 == 0:
            ext = 'jpg'
            fmt = 'JPEG'
        else:
            ext = 'png'
            fmt = 'PNG'

        img_path = directory / f'test_image_{i:04d}.{ext}'

        # Create colorful image
        img = Image.new('RGB', size, color=(i * 10 % 256, i * 20 % 256, i * 30 % 256))
        img.save(str(img_path), fmt, quality=95)
        images.append(img_path)

    print(f"Created {len(images)} test images")
    return images


async def benchmark_workers(
    workers: int,
    test_files: List[Tuple[str, str]],
    config: Config
) -> BenchmarkResult:
    """
    Benchmark with specific number of workers.

    Args:
        workers: Number of concurrent workers
        test_files: List of (source, dest) file pairs
        config: Configuration object

    Returns:
        Benchmark results
    """
    # Update config for this test
    config.max_concurrent_compressions = workers

    # Create components
    compressor = ImageCompressor(config)
    processor = FileProcessor(config, compressor)

    # Start monitoring
    process = psutil.Process()
    cpu_samples = []
    memory_samples = []

    # Monitoring task
    async def monitor():
        while True:
            cpu_samples.append(process.cpu_percent(interval=0.1))
            memory_samples.append(process.memory_info().rss / 1024 / 1024)  # MB
            await asyncio.sleep(0.1)

    monitor_task = asyncio.create_task(monitor())

    # Run benchmark
    start_time = time.time()
    result = await processor.process_batch(test_files)
    end_time = time.time()

    # Stop monitoring
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    total_time = end_time - start_time
    avg_cpu = sum(cpu_samples) / len(cpu_samples) if cpu_samples else 0
    peak_memory = max(memory_samples) if memory_samples else 0

    return BenchmarkResult(
        workers=workers,
        total_time=total_time,
        files_processed=result['success'],
        avg_cpu_percent=avg_cpu,
        peak_memory_mb=peak_memory
    )


async def run_benchmark(
    test_files_count: int,
    min_workers: int,
    max_workers: int
) -> List[BenchmarkResult]:
    """
    Run complete benchmark suite.

    Args:
        test_files_count: Number of test files to create
        min_workers: Minimum workers to test
        max_workers: Maximum workers to test

    Returns:
        List of benchmark results
    """
    print("="*70)
    print("Image Storage Service - Performance Benchmark")
    print("="*70)

    # Detect CPU info
    cpu_count = multiprocessing.cpu_count()
    print(f"CPU cores detected: {cpu_count}")
    print(f"Testing workers from {min_workers} to {max_workers}")
    print(f"Test images: {test_files_count}")
    print()

    # Create temporary directories
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        source_dir = tmppath / 'source'
        dest_dir = tmppath / 'dest'
        source_dir.mkdir()
        dest_dir.mkdir()

        # Create test images
        test_images = create_test_images(test_files_count, source_dir)

        # Create configuration
        config = Config(
            uncompressed_path=str(source_dir),
            compressed_path=str(dest_dir),
            min_file_size_kb=1,  # Process all test images
            max_resolution=1920,
            compression_quality=90,
            cache_maxsize=100,
            cache_ttl=60,
            log_level='WARNING',  # Suppress logs during benchmark
            max_concurrent_compressions=4,  # Will be overridden
            skip_existing_files=False
        )

        # Prepare file pairs
        test_files = [
            (str(img), str(dest_dir / img.name))
            for img in test_images
        ]

        # Run benchmarks
        print("\nRunning benchmarks...")
        print("="*70)
        results = []

        for workers in range(min_workers, max_workers + 1):
            # Recreate test files for each run
            for src, dst in test_files:
                if not os.path.exists(src):
                    # Copy from original if needed
                    idx = int(Path(src).stem.split('_')[-1])
                    original = test_images[idx]
                    if original.exists():
                        import shutil
                        shutil.copy2(str(original), src)

            result = await benchmark_workers(workers, test_files, config)
            results.append(result)
            print(result)

            # Cleanup dest files for next run
            for src, dst in test_files:
                if os.path.exists(dst):
                    os.remove(dst)
                # Ensure webp version is removed too
                webp_dst = dst.rsplit('.', 1)[0] + '.webp'
                if os.path.exists(webp_dst):
                    os.remove(webp_dst)

        print("="*70)
        return results


def analyze_results(results: List[BenchmarkResult]) -> None:
    """
    Analyze benchmark results and provide recommendations.

    Args:
        results: List of benchmark results
    """
    if not results:
        return

    print("\n" + "="*70)
    print("ANALYSIS & RECOMMENDATIONS")
    print("="*70)

    # Find best throughput
    best_throughput = max(results, key=lambda r: r.throughput)
    print(f"\n✓ Best throughput: {best_throughput.workers} workers ({best_throughput.throughput:.2f} files/s)")

    # Find best balance (throughput vs resources)
    # Score: throughput / (cpu_percent * memory_mb)
    scored_results = [
        (r, r.throughput / (r.avg_cpu_percent * r.peak_memory_mb / 1000))
        for r in results
    ]
    best_balance = max(scored_results, key=lambda x: x[1])[0]
    print(f"✓ Best balance: {best_balance.workers} workers (efficiency score: {scored_results[results.index(best_balance)][1]:.4f})")

    # Find fastest
    fastest = min(results, key=lambda r: r.total_time)
    print(f"✓ Fastest: {fastest.workers} workers ({fastest.total_time:.2f}s)")

    # Recommendations
    print("\n📊 RECOMMENDATIONS:")
    print(f"   • For maximum speed: {fastest.workers} workers")
    print(f"   • For best efficiency: {best_balance.workers} workers")
    print(f"   • Current auto-detect would use: {Config._calculate_optimal_concurrency()} workers")

    print("\n💡 To apply the recommended setting:")
    print(f"   Add to your .env file:")
    print(f"   MAX_CONCURRENT_COMPRESSIONS={best_balance.workers}")
    print("\n   Or leave it unset to use auto-detection.")
    print("="*70)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Benchmark Image Storage Service performance"
    )
    parser.add_argument(
        '--test-files',
        type=int,
        default=50,
        help='Number of test files to create (default: 50)'
    )
    parser.add_argument(
        '--min-workers',
        type=int,
        default=1,
        help='Minimum workers to test (default: 1)'
    )
    parser.add_argument(
        '--max-workers',
        type=int,
        default=min(multiprocessing.cpu_count() * 2, 16),
        help='Maximum workers to test (default: cpu_count * 2, max 16)'
    )

    args = parser.parse_args()

    try:
        results = await run_benchmark(
            test_files_count=args.test_files,
            min_workers=args.min_workers,
            max_workers=args.max_workers
        )
        analyze_results(results)
    except KeyboardInterrupt:
        print("\n\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nError during benchmark: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())

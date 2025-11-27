#!/usr/bin/env python3
"""
Diagnostic script to identify performance bottlenecks.
"""
import os
import sys
import multiprocessing
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Installing psutil...")
    os.system("pip install psutil")
    import psutil

from config import Config


def check_system():
    """Check system resources."""
    print("="*70)
    print("SYSTEM DIAGNOSTICS")
    print("="*70)

    # CPU
    cpu_count = multiprocessing.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
    cpu_avg = sum(cpu_percent) / len(cpu_percent)

    print(f"\n📊 CPU Information:")
    print(f"   Total cores: {cpu_count}")
    print(f"   Average usage: {cpu_avg:.1f}%")
    print(f"   Per-core usage: {cpu_percent}")

    # Memory
    memory = psutil.virtual_memory()
    print(f"\n💾 Memory Information:")
    print(f"   Total: {memory.total / 1024**3:.1f} GB")
    print(f"   Used: {memory.used / 1024**3:.1f} GB ({memory.percent}%)")
    print(f"   Available: {memory.available / 1024**3:.1f} GB")

    # Disk
    print(f"\n💿 Disk I/O:")
    disk_io = psutil.disk_io_counters()
    print(f"   Read: {disk_io.read_bytes / 1024**3:.2f} GB")
    print(f"   Write: {disk_io.write_bytes / 1024**3:.2f} GB")


def check_config():
    """Check current configuration."""
    print("\n" + "="*70)
    print("CONFIGURATION CHECK")
    print("="*70)

    try:
        config = Config.from_env()

        print(f"\n⚙️  Current Settings:")
        print(f"   Max concurrent: {config.max_concurrent_compressions}")
        print(f"   Skip existing: {config.skip_existing_files}")
        print(f"   Min file size: {config.min_file_size_kb} KB")
        print(f"   Compression quality: {config.compression_quality}%")

        # Check if auto-detected
        if os.getenv('MAX_CONCURRENT_COMPRESSIONS') is None:
            optimal = Config._calculate_optimal_concurrency()
            print(f"   Status: AUTO-DETECTED ({optimal} workers)")
        else:
            print(f"   Status: MANUALLY SET")
            optimal = Config._calculate_optimal_concurrency()
            current = config.max_concurrent_compressions
            if current < optimal:
                print(f"   ⚠️  WARNING: Set to {current} but {optimal} is optimal for your CPU!")

        return config
    except Exception as e:
        print(f"\n❌ Error loading config: {e}")
        return None


def check_directories(config):
    """Check source and destination directories."""
    print("\n" + "="*70)
    print("DIRECTORY CHECK")
    print("="*70)

    # Source directory
    print(f"\n📁 Source: {config.uncompressed_path}")
    if not os.path.exists(config.uncompressed_path):
        print(f"   ❌ Directory does not exist!")
        return

    # Count files
    total_files = 0
    compressible_files = 0
    already_processed = 0

    for root, dirs, files in os.walk(config.uncompressed_path):
        for file in files:
            file_path = os.path.join(root, file)
            total_files += 1

            # Check if compressible
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                try:
                    size_kb = os.path.getsize(file_path) / 1024
                    if size_kb >= config.min_file_size_kb:
                        compressible_files += 1
                    else:
                        already_processed += 1
                except:
                    pass

    print(f"   Total files: {total_files}")
    print(f"   Compressible: {compressible_files}")
    print(f"   Too small/other: {already_processed}")

    if compressible_files == 0:
        print(f"\n   ⚠️  WARNING: No files to compress!")
        print(f"      Reasons:")
        print(f"      - All files already processed")
        print(f"      - Files too small (< {config.min_file_size_kb} KB)")
        print(f"      - No JPEG/PNG files in directory")

    # Destination directory
    print(f"\n📁 Destination: {config.compressed_path}")
    if not os.path.exists(config.compressed_path):
        print(f"   ❌ Directory does not exist!")
        return

    dest_files = sum(1 for _, _, files in os.walk(config.compressed_path) for _ in files)
    print(f"   Processed files: {dest_files}")


def check_process():
    """Check running process."""
    print("\n" + "="*70)
    print("PROCESS CHECK")
    print("="*70)

    # Find the service process
    service_found = False
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'main.py' in ' '.join(cmdline):
                service_found = True
                print(f"\n✅ Service is running:")
                print(f"   PID: {proc.info['pid']}")
                print(f"   CPU: {proc.cpu_percent(interval=0.5)}%")
                print(f"   Memory: {proc.memory_info().rss / 1024**2:.1f} MB")
                print(f"   Threads: {proc.num_threads()}")

                # Check CPU per thread
                try:
                    threads = proc.threads()
                    print(f"   Thread details: {len(threads)} threads")
                except:
                    pass

                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    if not service_found:
        print(f"\n❌ Service is not running!")
        print(f"   Start it with: ./start.sh")


def diagnose_bottleneck(config):
    """Diagnose what the bottleneck is."""
    print("\n" + "="*70)
    print("BOTTLENECK ANALYSIS")
    print("="*70)

    cpu_percent = psutil.cpu_percent(interval=1)

    print(f"\n🔍 Analysis:")

    if cpu_percent < 20:
        print(f"   ⚠️  CPU usage is LOW ({cpu_percent}%)")
        print(f"\n   Possible causes:")
        print(f"   1. No files to process → Check source directory")
        print(f"   2. MAX_CONCURRENT_COMPRESSIONS too low → Increase value")
        print(f"   3. Files too small → Check MIN_FILE_SIZE_KB")
        print(f"   4. Disk I/O bottleneck → Check disk speed")
        print(f"   5. Network storage slow → Use local disk")

        # Check concurrency
        if config and config.max_concurrent_compressions < 4:
            print(f"\n   💡 RECOMMENDATION:")
            print(f"      Increase MAX_CONCURRENT_COMPRESSIONS to {Config._calculate_optimal_concurrency()}")

    elif cpu_percent < 50:
        print(f"   ℹ️  CPU usage is MODERATE ({cpu_percent}%)")
        print(f"      System has capacity for more work")
        print(f"\n   💡 RECOMMENDATION:")
        print(f"      Increase MAX_CONCURRENT_COMPRESSIONS by 2-4")

    elif cpu_percent < 80:
        print(f"   ✅ CPU usage is GOOD ({cpu_percent}%)")
        print(f"      System is well-utilized")

    else:
        print(f"   🔥 CPU usage is HIGH ({cpu_percent}%)")
        print(f"      System is fully utilized (good!)")


def main():
    """Run diagnostics."""
    print("\n" + "="*70)
    print("IMAGE STORAGE SERVICE - DIAGNOSTIC TOOL")
    print("="*70)

    check_system()
    config = check_config()

    if config:
        check_directories(config)

    check_process()

    if config:
        diagnose_bottleneck(config)

    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)

    cpu_count = multiprocessing.cpu_count()
    optimal = Config._calculate_optimal_concurrency() if config else max(2, int(cpu_count * 0.75))

    print(f"\n💡 Quick Fixes:")
    print(f"\n1. Increase concurrency:")
    print(f"   echo 'MAX_CONCURRENT_COMPRESSIONS={optimal}' >> .env")
    print(f"   ./restart.sh")

    print(f"\n2. Check if files are being processed:")
    print(f"   ./watch_logs.sh INFO | grep 'Compressed'")

    print(f"\n3. Check queue size:")
    print(f"   ./watch_logs.sh INFO | grep 'batch'")

    print(f"\n4. Monitor CPU in real-time:")
    print(f"   ./status.sh")

    print("\n" + "="*70)


if __name__ == '__main__':
    main()

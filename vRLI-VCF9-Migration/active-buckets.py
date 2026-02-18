#!/usr/bin/env python3

import subprocess
import re
import argparse
import sys
from datetime import datetime

def format_ms_to_date(ms_timestamp):
    """Converts UNIX epoch in milliseconds to a formatted date string."""
    dt = datetime.fromtimestamp(ms_timestamp / 1000.0)
    return dt.strftime("%d.%m.%Y-%H:%M:%S")

def format_size(size_bytes):
    """Converts raw bytes to a human-readable string."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    p = size_bytes
    while p >= 1024 and i < len(size_name) - 1:
        p /= 1024.0
        i += 1
    return f"{p:.2f} {size_name[i]}"

def main():
    # Set up help text
    description_text = (
        "VMware Aria Operations for Logs / vRealize Log Insight Active Bucket Lister\n\n"
        "This script executes the 'bucket-index show' command and lists all buckets\n"
        "that are currently 'active' (not archived), along with their start times and sizes."
    )

    parser = argparse.ArgumentParser(
        description=description_text,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.parse_args()

    # Execute the loginsight bucket-index command
    cmd = ["/usr/lib/loginsight/application/sbin/bucket-index", "show"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout
    except FileNotFoundError:
        print("Error: The bucket-index command was not found. Are you running this on the Log Insight node?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Command execution failed with return code {e.returncode}")
        print(e.stderr)
        sys.exit(1)

    active_buckets = []

    # Parse the output
    for line in output.splitlines():
        if "status=active" in line:
            # Extract fields
            id_match = re.search(r'id=([a-f0-9\-]+)', line)
            start_match = re.search(r'startTime=(\d+)', line)
            size_match = re.search(r'size=(\d+)', line)

            if id_match:
                bucket_id = id_match.group(1)
                
                # Handle start time
                if start_match:
                    start_ms = int(start_match.group(1))
                    start_time_str = format_ms_to_date(start_ms)
                else:
                    start_time_str = "N/A (cmd=[NULL])"
                
                # Handle size
                size_bytes = int(size_match.group(1)) if size_match else 0
                
                active_buckets.append((bucket_id, start_time_str, size_bytes))

    # Output the results
    print(f"\n--- Active Buckets ---")
    print(f"Found {len(active_buckets)} active bucket(s).\n")
    
    if active_buckets:
        # Print table header
        print(f"{'BUCKET ID'.ljust(40)} | {'START TIME'.ljust(22)} | SIZE")
        print("-" * 85)
        
        # Print rows
        for b_id, b_time, b_size in active_buckets:
            human_size = format_size(b_size)
            print(f"{b_id.ljust(40)} | {b_time.ljust(22)} | {b_size} bytes ({human_size})")
        print()

if __name__ == "__main__":
    main()
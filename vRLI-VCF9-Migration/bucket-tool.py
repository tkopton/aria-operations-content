#!/usr/bin/env python3

import subprocess
import re
import argparse
import sys
from datetime import datetime

# --- Helper Functions ---

def parse_date_to_ms(date_str):
    """Converts a date string (dd.mm.yyyy-hh:mm:ss) to UNIX epoch in milliseconds."""
    try:
        dt = datetime.strptime(date_str, "%d.%m.%Y-%H:%M:%S")
        return int(dt.timestamp() * 1000)
    except ValueError as e:
        print(f"Error parsing date '{date_str}': {e}")
        print("Please ensure you use the format: dd.mm.yyyy-hh:mm:ss")
        sys.exit(1)

def format_ms_to_date(ms_timestamp):
    """Converts UNIX epoch in milliseconds to a formatted date string."""
    dt = datetime.fromtimestamp(ms_timestamp / 1000.0)
    return dt.strftime("%d.%m.%Y-%H:%M:%S")

def format_size(size_bytes):
    """Converts raw bytes to a human-readable string (KB, MB, GB, etc.)."""
    if size_bytes == 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    p = float(size_bytes)
    while p >= 1024 and i < len(size_name) - 1:
        p /= 1024.0
        i += 1
    return f"{p:.2f} {size_name[i]}"

def get_bucket_output():
    """Executes the Log Insight bucket-index command and returns the output."""
    cmd = ["/usr/lib/loginsight/application/sbin/bucket-index", "show"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout
    except FileNotFoundError:
        print("Error: The bucket-index command was not found. Are you running this on the Log Insight node?")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Command execution failed with return code {e.returncode}")
        print(e.stderr)
        sys.exit(1)

# --- Subcommand Handlers ---

def handle_archived_size(args):
    """Calculates the sum of sizes for archived buckets in a date range."""
    user_start_ms = parse_date_to_ms(args.start_date)
    user_end_ms = parse_date_to_ms(args.end_date)
    
    output = get_bucket_output()
    
    total_size_bytes = 0
    matched_ids = []

    for line in output.splitlines():
        if "status=archived" in line:
            id_match = re.search(r'id=([a-f0-9\-]+)', line)
            size_match = re.search(r'size=(\d+)', line)
            start_match = re.search(r'startTime=(\d+)', line)
            end_match = re.search(r'endTime=(\d+)', line)

            if id_match and size_match and start_match and end_match:
                bucket_id = id_match.group(1)
                size = int(size_match.group(1))
                start_time = int(start_match.group(1))
                end_time = int(end_match.group(1))

                # Overlap logic: bucket starts before user's end time AND ends after user's start time
                if start_time <= user_end_ms and end_time >= user_start_ms:
                    total_size_bytes += size
                    matched_ids.append(bucket_id)

    print(f"\n--- Archived Buckets Summary (Date Range) ---")
    print(f"Found {len(matched_ids)} archived bucket(s) overlapping the timeframe.\n")
    
    if matched_ids:
        print("Matched Bucket IDs:")
        for b_id in matched_ids:
            print(f" - {b_id}")
        print()

    print(f"Total size: {total_size_bytes} bytes ({format_size(total_size_bytes)})\n")

def handle_list_active(args):
    """Lists all active buckets with their start times and sizes."""
    output = get_bucket_output()
    active_buckets = []

    for line in output.splitlines():
        if "status=active" in line:
            id_match = re.search(r'id=([a-f0-9\-]+)', line)
            start_match = re.search(r'startTime=(\d+)', line)
            size_match = re.search(r'size=(\d+)', line)

            if id_match:
                bucket_id = id_match.group(1)
                
                if start_match:
                    start_time_str = format_ms_to_date(int(start_match.group(1)))
                else:
                    start_time_str = "N/A (cmd=[NULL])"
                
                size_bytes = int(size_match.group(1)) if size_match else 0
                active_buckets.append((bucket_id, start_time_str, size_bytes))

    print(f"\n--- Active Buckets ---")
    print(f"Found {len(active_buckets)} active bucket(s).\n")
    
    if active_buckets:
        print(f"{'BUCKET ID'.ljust(40)} | {'START TIME'.ljust(19)} | SIZE")
        print("-" * 85)
        for b_id, b_time, b_size in active_buckets:
            human_size = format_size(b_size)
            print(f"{b_id.ljust(40)} | {b_time.ljust(19)} | {b_size} bytes ({human_size})")
        print()

def handle_list_archived(args):
    """Lists all archived buckets with start/end times and calculates total size."""
    output = get_bucket_output()
    archived_buckets = []
    total_size_bytes = 0

    for line in output.splitlines():
        if "status=archived" in line:
            id_match = re.search(r'id=([a-f0-9\-]+)', line)
            size_match = re.search(r'size=(\d+)', line)
            start_match = re.search(r'startTime=(\d+)', line)
            end_match = re.search(r'endTime=(\d+)', line)

            if id_match and size_match and start_match and end_match:
                bucket_id = id_match.group(1)
                size = int(size_match.group(1))
                start_time_str = format_ms_to_date(int(start_match.group(1)))
                end_time_str = format_ms_to_date(int(end_match.group(1)))
                
                archived_buckets.append((bucket_id, start_time_str, end_time_str, size))
                total_size_bytes += size

    print(f"\n--- All Archived Buckets ---")
    print(f"Found {len(archived_buckets)} archived bucket(s).\n")
    
    if archived_buckets:
        # Table Header
        print(f"{'BUCKET ID'.ljust(40)} | {'START TIME'.ljust(19)} | {'END TIME'.ljust(19)} | SIZE")
        print("-" * 110)
        
        # Table Rows
        for b_id, b_start, b_end, b_size in archived_buckets:
            human_size = format_size(b_size)
            print(f"{b_id.ljust(40)} | {b_start.ljust(19)} | {b_end.ljust(19)} | {b_size} bytes ({human_size})")
        
        print("-" * 110)
        
    print(f"\nGrand Total Size: {total_size_bytes} bytes ({format_size(total_size_bytes)})\n")

# --- Main Entry Point ---

def main():
    parser = argparse.ArgumentParser(
        description="VMware Aria Operations for Logs / vRealize Log Insight Bucket Tool",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(title="Commands", dest="command", required=True)

    # Subparser for 'archived-size' (Date range specific)
    parser_archived = subparsers.add_parser(
        "archived-size", 
        help="Calculate the total size of archived buckets within a specific date range."
    )
    parser_archived.add_argument("start_date", help="Start date (dd.mm.yyyy-hh:mm:ss)")
    parser_archived.add_argument("end_date", help="End date (dd.mm.yyyy-hh:mm:ss)")
    parser_archived.set_defaults(func=handle_archived_size)

    # Subparser for 'list-active'
    parser_active = subparsers.add_parser(
        "list-active", 
        help="List all currently active buckets along with start times and sizes."
    )
    parser_active.set_defaults(func=handle_list_active)

    # Subparser for 'list-archived' (All archived buckets)
    parser_list_archived = subparsers.add_parser(
        "list-archived", 
        help="List all archived buckets with start/end times and calculate grand total size."
    )
    parser_list_archived.set_defaults(func=handle_list_archived)

    args = parser.parse_args()
    
    # Execute the appropriate function based on the subcommand
    args.func(args)

if __name__ == "__main__":
    main()
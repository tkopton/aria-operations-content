#!/usr/bin/env python3

import subprocess
import re
import argparse
from datetime import datetime
import sys

def parse_date_to_ms(date_str):
    """Converts a date string (dd.mm.yyyy-hh:mm:ss) to UNIX epoch in milliseconds."""
    dt = datetime.strptime(date_str, "%d.%m.%Y-%H:%M:%S")
    return int(dt.timestamp() * 1000)

def main():
    # Set up detailed help text
    description_text = (
        "VMware Aria Operations for Logs / vRealize Log Insight Bucket Size Calculator\n\n"
        "This script executes the 'bucket-index show' command and calculates the total size\n"
        "of all 'archived' buckets that overlap with a specified date range."
    )
    
    epilog_text = (
        "OUTPUT EXPLANATION:\n"
        "-------------------\n"
        "The script prints the following information:\n"
        "1. Total Count : The number of archived buckets matching your timeframe.\n"
        "2. Matched IDs : The specific UUIDs of the buckets included in the calculation.\n"
        "                 (A bucket is included if its start/end times overlap with your input).\n"
        "3. Total Size  : The exact combined size of the matched buckets in bytes.\n"
        "4. Human Size  : The combined size converted to Gigabytes (GB).\n\n"
        "EXAMPLE USAGE:\n"
        "  ./calc_bucket_size.py 11.02.2026-00:00:00 16.02.2026-23:59:59"
    )

    parser = argparse.ArgumentParser(
        description=description_text,
        epilog=epilog_text,
        formatter_class=argparse.RawTextHelpFormatter # Allows newlines in description/epilog
    )
    
    parser.add_argument("start_date", help="Start date in the exact format: dd.mm.yyyy-hh:mm:ss")
    parser.add_argument("end_date", help="End date in the exact format: dd.mm.yyyy-hh:mm:ss")
    
    args = parser.parse_args()

    try:
        user_start_ms = parse_date_to_ms(args.start_date)
        user_end_ms = parse_date_to_ms(args.end_date)
    except ValueError as e:
        print(f"Error parsing dates: {e}")
        print("Please ensure you use the format: dd.mm.yyyy-hh:mm:ss")
        sys.exit(1)

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

    total_size_bytes = 0
    matched_ids = []

    # Parse the output
    for line in output.splitlines():
        if "status=archived" in line:
            # Extract fields using regex
            id_match = re.search(r'id=([a-f0-9\-]+)', line)
            size_match = re.search(r'size=(\d+)', line)
            start_match = re.search(r'startTime=(\d+)', line)
            end_match = re.search(r'endTime=(\d+)', line)

            if id_match and size_match and start_match and end_match:
                bucket_id = id_match.group(1)
                size = int(size_match.group(1))
                start_time = int(start_match.group(1))
                end_time = int(end_match.group(1))

                # Check for overlap: bucket starts before user's end time AND ends after user's start time
                if start_time <= user_end_ms and end_time >= user_start_ms:
                    total_size_bytes += size
                    matched_ids.append(bucket_id)

    # Output the results
    print(f"\n--- Results ---")
    print(f"Found {len(matched_ids)} archived bucket(s) in the specified time range.\n")
    
    if matched_ids:
        print("Matched Bucket IDs:")
        for b_id in matched_ids:
            print(f" - {b_id}")
        print()

    print(f"Total size: {total_size_bytes} bytes")
    
    # Human readable format
    gb_size = total_size_bytes / (1024**3)
    print(f"Human readable: {gb_size:.2f} GB")

if __name__ == "__main__":
    main()
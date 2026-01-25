#!/usr/bin/env python3
"""
Keep-alive script for Streamlit Cloud app.
Pings the app periodically to prevent it from going to sleep.
"""

import requests
import time
import sys
from datetime import datetime

# Default Streamlit app URL - update this to your actual app URL
DEFAULT_URL = "https://midwinter-manual.streamlit.app/"

def ping_app(url: str) -> bool:
    """Ping the app and return True if successful."""
    try:
        response = requests.get(url, timeout=30)
        return response.status_code == 200
    except requests.RequestException as e:
        print(f"  Error: {e}")
        return False

def main():
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300  # 5 minutes default

    print(f"Keep-alive for: {url}")
    print(f"Ping interval: {interval} seconds")
    print("Press Ctrl+C to stop\n")

    ping_count = 0
    success_count = 0

    try:
        while True:
            ping_count += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{timestamp}] Ping #{ping_count}...", end=" ")

            if ping_app(url):
                success_count += 1
                print("OK")
            else:
                print("FAILED")

            print(f"  Success rate: {success_count}/{ping_count} ({100*success_count/ping_count:.1f}%)")
            time.sleep(interval)

    except KeyboardInterrupt:
        print(f"\n\nStopped. Total pings: {ping_count}, Successful: {success_count}")

if __name__ == "__main__":
    main()

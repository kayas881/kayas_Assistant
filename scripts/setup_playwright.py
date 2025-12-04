#!/usr/bin/env python3
"""
Setup Playwright browsers and validate installation.
"""
import sys
import subprocess

def run(cmd: list[str]) -> int:
    print(f"$ {' '.join(cmd)}")
    try:
        return subprocess.call(cmd)
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    rc = run([sys.executable, "-m", "pip", "install", "playwright"])
    if rc != 0:
        sys.exit(rc)
    rc = run([sys.executable, "-m", "playwright", "install", "chromium"])
    sys.exit(rc)

#!/usr/bin/env python3
"""
SIMPLE: Use the interactive tester which works perfectly
"""

import subprocess
import sys

if __name__ == "__main__":
    print("\n" + "="*70)
    print("KAYAS MULTI-STEP TASK EXECUTION".center(70))
    print("="*70 + "\n")
    
    print("This starts the interactive multi-step task executor.")
    print("Enter tasks like:")
    print("  • 'open notepad and write hello'")
    print("  • 'search for python and save to file'")
    print("  • 'open chrome and search for tutorials'\n")
    
    # Just run the interactive tester
    subprocess.run([sys.executable, "interactive_multistep_test.py"])


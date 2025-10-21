#!/usr/bin/env python3
"""
Quick feedback submission script for testing preference model training.
Usage: python scripts/submit_feedback.py <run_id> "<feedback_text>" [tags]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.memory.sqlite_memory import SQLiteMemory, MemoryConfig
from src.agent.config import db_path


def main():
    parser = argparse.ArgumentParser(description="Submit feedback for a run")
    parser.add_argument("run_id", help="Run ID to provide feedback for")
    parser.add_argument("feedback", help="Feedback text")
    parser.add_argument("--tags", default="", help="Tags (e.g., 'pos' or 'neg')")
    
    args = parser.parse_args()
    
    memory = SQLiteMemory(MemoryConfig(db_path=db_path()))
    memory.log_feedback(args.run_id, args.feedback, args.tags)
    
    print(f"✓ Feedback logged for run {args.run_id}")
    print(f"  Feedback: {args.feedback}")
    print(f"  Tags: {args.tags}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
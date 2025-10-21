#!/usr/bin/env python3
"""
Simple CLI script to train the preference model locally.
Usage: python scripts/train_preference.py [--epochs N] [--vocab-size N] [--lr 0.1]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path so we can import src modules
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.training.preference_model import train_preference_model, PrefConfig
from src.agent.config import db_path, preference_model_path


def main():
    parser = argparse.ArgumentParser(description="Train preference model from feedback")
    parser.add_argument("--epochs", type=int, default=5, help="Training epochs (default: 5)")
    parser.add_argument("--vocab-size", type=int, default=5000, help="Max vocabulary size (default: 5000)")
    parser.add_argument("--lr", type=float, default=0.1, help="Learning rate (default: 0.1)")
    parser.add_argument("--force", action="store_true", help="Train even if no labeled feedback found")
    
    args = parser.parse_args()
    
    print(f"Training preference model...")
    print(f"  Database: {db_path()}")
    print(f"  Model output: {preference_model_path()}")
    print(f"  Epochs: {args.epochs}, Vocab: {args.vocab_size}, LR: {args.lr}")
    
    cfg = PrefConfig(
        db_file=db_path(),
        model_file=preference_model_path(),
        max_vocab=args.vocab_size,
        epochs=args.epochs,
        lr=args.lr,
    )
    
    try:
        model = train_preference_model(cfg)
        print(f"✓ Training complete!")
        print(f"  Vocabulary size: {len(model.vocab)}")
        print(f"  Model saved to: {preference_model_path()}")
        
        # Quick test score
        test_prompt = "Goal: Create a file with notes"
        test_completion = '[{"tool": "filesystem.create_file", "args": {"filename": "notes.txt", "content": "test"}}]'
        score = model.score(test_prompt, test_completion)
        print(f"  Test score: {score:.3f}")
        
    except Exception as e:
        print(f"✗ Training failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
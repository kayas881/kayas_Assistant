"""
Regenerate training files from all collected PNG screenshots
Creates complete train.jsonl from all samples in training_data_auto/
"""

import json
from pathlib import Path
from PIL import Image
import re

def main():
    data_dir = Path("training_data_auto")
    
    # Find all screenshot PNGs
    screenshots = sorted(data_dir.glob("frame_*.png"))
    print(f"Found {len(screenshots)} screenshot files")
    
    # Load existing dataset.json if it exists
    dataset_file = data_dir / "dataset.json"
    samples_by_screenshot = {}
    
    if dataset_file.exists():
        with open(dataset_file, "r") as f:
            dataset = json.load(f)
            for sample in dataset.get("samples", []):
                if "screenshot" in sample:
                    samples_by_screenshot[sample["screenshot"]] = sample
        print(f"Loaded {len(samples_by_screenshot)} samples from dataset.json")
    
    # Create training file
    train_file = data_dir / "train.jsonl"
    samples_written = 0
    
    with open(train_file, "w") as f:
        for screenshot_path in screenshots:
            screenshot_name = screenshot_path.name
            
            # Get sample data if available, otherwise create basic entry
            if screenshot_name in samples_by_screenshot:
                sample = samples_by_screenshot[screenshot_name]
                example = {
                    "image": screenshot_name,
                    "elements": sample.get("elements", []),
                    "num_elements": sample.get("num_elements", 0)
                }
                if "action" in sample:
                    example["action"] = sample["action"]
            else:
                # Create minimal entry for screenshots without metadata
                example = {
                    "image": screenshot_name,
                    "elements": [],
                    "num_elements": 0
                }
            
            f.write(json.dumps(example) + "\n")
            samples_written += 1
    
    print(f"\nCreated {train_file}")
    print(f"Total training samples: {samples_written}")
    
    # Update dataset.json with correct count
    if dataset_file.exists():
        with open(dataset_file, "r") as f:
            dataset = json.load(f)
        
        dataset["num_samples"] = len(screenshots)
        
        with open(dataset_file, "w") as f:
            json.dump(dataset, f, indent=2)
        
        print(f"Updated dataset.json with correct sample count: {len(screenshots)}")

if __name__ == "__main__":
    main()

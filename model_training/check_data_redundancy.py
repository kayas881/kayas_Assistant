import json
from pathlib import Path

# Load both files
dataset_path = Path("training_data_auto/dataset.json")
bboxes_path = Path("training_data_auto/bboxes.json")

print("Loading files...")
with open(dataset_path) as f:
    dataset = json.load(f)

with open(bboxes_path) as f:
    bboxes = json.load(f)

# Analyze dataset.json
samples = dataset.get('samples', [])
print(f"\n📊 dataset.json:")
print(f"   Total samples: {len(samples)}")

if samples:
    sample = samples[0]
    print(f"   Sample keys: {list(sample.keys())}")
    if 'elements' in sample:
        print(f"   Elements in first sample: {len(sample['elements'])}")
        if sample['elements']:
            print(f"   Element keys: {list(sample['elements'][0].keys())}")

# Analyze bboxes.json
print(f"\n📊 bboxes.json:")
print(f"   Total frames: {len(bboxes)}")
if bboxes:
    first_frame = list(bboxes.keys())[0]
    first_frame_data = bboxes[first_frame]
    print(f"   First frame: {first_frame}")
    print(f"   Elements in first frame: {len(first_frame_data)}")
    if first_frame_data:
        print(f"   Element keys: {list(first_frame_data[0].keys())}")

# Check for redundancy
print("\n🔍 Redundancy Analysis:")

# Count total elements in both structures
if samples and 'elements' in samples[0]:
    total_dataset_elements = sum(len(s.get('elements', [])) for s in samples)
    total_bbox_elements = sum(len(v) for v in bboxes.values())
    
    print(f"   Total UI elements in dataset.json: {total_dataset_elements:,}")
    print(f"   Total UI elements in bboxes.json: {total_bbox_elements:,}")
    
    if total_dataset_elements == total_bbox_elements:
        print("\n   ⚠️  SAME COUNT! Likely the same data in different formats")
        
        # Compare actual content
        if samples[0]['elements'] and bboxes:
            first_sample_screenshot = samples[0]['screenshot']
            if first_sample_screenshot in bboxes:
                dataset_elem = samples[0]['elements'][0]
                bbox_elem = bboxes[first_sample_screenshot][0]
                
                print("\n   Comparing first element from same frame:")
                print(f"   Dataset: {dataset_elem}")
                print(f"   Bboxes:  {bbox_elem}")
                
                # Check if data is identical
                if dataset_elem == bbox_elem:
                    print("\n   ✅ CONFIRMED: Data is IDENTICAL!")
                    print("   → bboxes.json is 100% REDUNDANT")
                else:
                    # Check key overlap
                    dataset_keys = set(dataset_elem.keys())
                    bbox_keys = set(bbox_elem.keys())
                    common_keys = dataset_keys & bbox_keys
                    
                    print(f"\n   Common keys: {common_keys}")
                    print(f"   Dataset-only keys: {dataset_keys - bbox_keys}")
                    print(f"   Bboxes-only keys: {bbox_keys - dataset_keys}")
    else:
        print(f"\n   ℹ️  Different counts: dataset has {total_dataset_elements:,}, bboxes has {total_bbox_elements:,}")

# Training recommendation
print("\n\n🎯 TRAINING RECOMMENDATION:")
if samples:
    print(f"   ✅ Use dataset.json ONLY ({len(samples):,} samples)")
    print(f"   ❌ bboxes.json is NOT needed for training")
    print(f"\n   Why? dataset.json already contains:")
    print(f"   • Screenshots (image paths)")
    print(f"   • UI elements with bboxes")
    print(f"   • Element metadata (type, name, text)")
    print(f"\n   The training notebook loads dataset.json and that's sufficient!")

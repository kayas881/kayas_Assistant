"""
Rebuild dataset.json to include all PNG screenshots with their bboxes metadata
"""
import json
from pathlib import Path
from datetime import datetime
from tqdm import tqdm

def rebuild_dataset():
    """Rebuild dataset.json from all frame_*.png files and bboxes.json"""
    
    data_dir = Path("training_data_auto")
    
    if not data_dir.exists():
        print(f"❌ Directory not found: {data_dir}")
        return
    
    # Load bboxes if available
    bboxes_file = data_dir / "bboxes.json"
    bboxes_data = {}
    if bboxes_file.exists():
        print("📦 Loading bboxes.json...")
        with open(bboxes_file) as f:
            bboxes_data = json.load(f)
        print(f"   Found bbox data for {len(bboxes_data)} images")
    
    # Find all frame PNG files
    print("\n🔍 Finding all frame_*.png files...")
    frame_files = sorted(data_dir.glob("frame_*.png"))
    print(f"   Found {len(frame_files)} screenshot files")
    
    if len(frame_files) == 0:
        print("❌ No frame_*.png files found!")
        return
    
    # Build samples array
    print("\n🔨 Building dataset samples...")
    samples = []
    
    for img_path in tqdm(frame_files, desc="Processing"):
        img_name = img_path.name
        
        # Extract frame number from filename
        try:
            frame_num = int(img_name.split('_')[1].split('.')[0])
        except:
            frame_num = len(samples)
        
        # Create sample entry
        sample = {
            "id": frame_num,
            "screenshot": img_name,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add bbox/element data if available
        if img_name in bboxes_data:
            elements = bboxes_data[img_name]
            sample["elements"] = elements
        else:
            sample["elements"] = []
        
        samples.append(sample)
    
    # Create full dataset structure
    dataset = {
        "num_samples": len(samples),
        "created_at": datetime.now().isoformat(),
        "rebuilt": True,
        "samples": samples
    }
    
    # Save dataset.json
    output_file = data_dir / "dataset.json"
    print(f"\n💾 Saving to {output_file}...")
    
    with open(output_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"\n✅ Dataset rebuilt successfully!")
    print(f"   Total samples: {len(samples):,}")
    print(f"   Samples with elements: {sum(1 for s in samples if s['elements']):,}")
    print(f"   File size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    # Verify by loading it back
    print("\n🔍 Verifying...")
    with open(output_file) as f:
        verify = json.load(f)
    
    print(f"   Verified: {verify['num_samples']:,} samples in dataset.json")
    print(f"   Ready for training! 🚀")

if __name__ == "__main__":
    rebuild_dataset()

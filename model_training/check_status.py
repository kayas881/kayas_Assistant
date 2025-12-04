"""
Collection Status Monitor

Check the status of your overnight collection without opening files.
Shows real-time progress, sample counts, and any issues.
"""

import json
from pathlib import Path
from datetime import datetime
import sys

def format_size(bytes):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes < 1024:
            return f"{bytes:.1f} {unit}"
        bytes /= 1024
    return f"{bytes:.1f} TB"

def main():
    output_dir = Path("training_data_auto")
    
    if not output_dir.exists():
        print("❌ Collection not started yet (training_data_auto folder not found)")
        sys.exit(1)
    
    print("\n" + "="*70)
    print(" "*20 + "COLLECTION STATUS MONITOR")
    print("="*70 + "\n")
    
    # Check progress file
    progress_file = output_dir / "progress.json"
    if progress_file.exists():
        with open(progress_file, "r") as f:
            app_results = json.load(f)
        
        completed = sum(1 for r in app_results.values() if r.get("completed", False))
        total_apps = len(app_results)
        total_samples = sum(r["samples"] for r in app_results.values())
        target_samples = sum(r["target"] for r in app_results.values())
        
        print(f"📊 PROGRESS OVERVIEW")
        print("-"*70)
        print(f"   Apps Completed: {completed}/{total_apps}")
        print(f"   Samples Collected: {total_samples:,}/{target_samples:,}")
        print(f"   Success Rate: {(total_samples/target_samples*100):.1f}%")
        print()
        
        print(f"📱 PER-APP RESULTS")
        print("-"*70)
        
        for app, result in sorted(app_results.items()):
            samples = result["samples"]
            target = result["target"]
            completed_flag = result.get("completed", False)
            
            # Status emoji
            if completed_flag:
                status = "✅"
            elif samples > 0:
                status = "⚠️"
            else:
                status = "❌"
            
            # Progress bar
            if target > 0:
                pct = (samples / target) * 100
                bar_length = 20
                filled = int(bar_length * samples / target)
                bar = "█" * filled + "░" * (bar_length - filled)
                print(f"   {status} {app:12s} [{bar}] {samples:4d}/{target:4d} ({pct:5.1f}%)")
            else:
                print(f"   {status} {app:12s} [No target set]")
        
        print()
        
        # Check for errors
        errors = [(app, r.get("error")) for app, r in app_results.items() if "error" in r]
        if errors:
            print(f"⚠️  ERRORS DETECTED")
            print("-"*70)
            for app, error in errors:
                print(f"   {app}: {error}")
            print()
    else:
        print("⏳ Collection in progress (no progress file yet)...")
        print()
    
    # Count actual files
    screenshots = list(output_dir.glob("frame_*.png"))
    if screenshots:
        total_size = sum(f.stat().st_size for f in screenshots)
        print(f"💾 FILE STATISTICS")
        print("-"*70)
        print(f"   Screenshot Files: {len(screenshots):,}")
        print(f"   Total Size: {format_size(total_size)}")
        print()
    
    # Check dataset file
    dataset_file = output_dir / "dataset.json"
    if dataset_file.exists():
        try:
            with open(dataset_file, "r") as f:
                dataset = json.load(f)
            
            num_samples = dataset.get("num_samples", 0)
            created = dataset.get("created_at", "Unknown")
            
            print(f"📦 DATASET STATUS")
            print("-"*70)
            print(f"   Samples in Dataset: {num_samples:,}")
            print(f"   Last Updated: {created}")
            print()
        except:
            print("⚠️  Dataset file exists but couldn't be read")
            print()
    
    # Check training file
    train_file = output_dir / "train.jsonl"
    if train_file.exists():
        with open(train_file, "r") as f:
            train_lines = sum(1 for _ in f)
        
        print(f"🎓 TRAINING FILES")
        print("-"*70)
        print(f"   Training Samples: {train_lines:,}")
        print(f"   ✅ Ready for upload to Google Colab")
        print()
    
    # Check report
    report_file = output_dir / "COLLECTION_REPORT.txt"
    if report_file.exists():
        print(f"📄 DETAILED REPORT")
        print("-"*70)
        print(f"   Available: {report_file}")
        print(f"   Run: type {report_file}")
        print()
    
    # Recommendations
    if progress_file.exists():
        with open(progress_file, "r") as f:
            app_results = json.load(f)
        
        failed = [(app, r["samples"], r["target"]) for app, r in app_results.items() 
                  if r["samples"] < r["target"] * 0.8]
        
        if failed:
            print(f"💡 RECOMMENDATIONS")
            print("-"*70)
            print(f"   {len(failed)} app(s) need retry:")
            for app, samples, target in failed:
                print(f"      • {app}: {samples}/{target} samples")
            print()
            print(f"   Run: python retry_failed_apps.py")
            print()
        else:
            print(f"✅ ALL APPS COMPLETED SUCCESSFULLY!")
            print("-"*70)
            print(f"   Next steps:")
            print(f"      1. Restore power settings: .\restore_power_settings.ps1")
            print(f"      2. Compress: Compress-Archive training_data_auto training_data.zip")
            print(f"      3. Upload to Google Colab")
            print(f"      4. Start fine-tuning!")
            print()
    
    print("="*70)
    print()

if __name__ == "__main__":
    main()

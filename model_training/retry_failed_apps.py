"""
Retry Failed Apps Script

Automatically retries apps that didn't collect enough samples in the overnight run.
Reads progress.json and re-runs only apps that need more data.
"""

import json
from pathlib import Path
import subprocess
import sys

def main():
    progress_file = Path("training_data_auto/progress.json")
    
    if not progress_file.exists():
        print("❌ No progress.json found. Run the main collector first.")
        sys.exit(1)
    
    # Load progress
    with open(progress_file, "r") as f:
        app_results = json.load(f)
    
    # Find apps that need retry
    failed_apps = []
    for app, result in app_results.items():
        samples = result.get("samples", 0)
        target = result.get("target", 500)
        
        if samples < target * 0.8:  # Less than 80% success
            needed = target - samples
            failed_apps.append((app, samples, needed))
    
    if not failed_apps:
        print("✅ All apps completed successfully!")
        print("\nCollection Summary:")
        for app, result in app_results.items():
            print(f"  {app}: {result['samples']}/{result['target']} samples")
        return
    
    print("="*60)
    print("RETRY FAILED APPS")
    print("="*60)
    print(f"\nFound {len(failed_apps)} apps needing retry:\n")
    
    for app, collected, needed in failed_apps:
        print(f"  • {app}: {collected} collected, {needed} more needed")
    
    print("\n" + "="*60)
    print("Starting retry collection...")
    print("="*60 + "\n")
    
    # Retry each failed app
    for app, collected, needed in failed_apps:
        print(f"\n[RETRY] {app} - collecting {needed} more samples...")
        
        # Run collector for this app
        cmd = [
            sys.executable,
            "automated_collector.py",
            "--apps", app,
            "--samples-per-app", str(needed),
            "--output", "training_data_auto"
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ {app} retry completed")
        except subprocess.CalledProcessError as e:
            print(f"❌ {app} retry failed: {e}")
        except KeyboardInterrupt:
            print("\n⚠️ Retry interrupted by user")
            break
    
    # Final summary
    print("\n" + "="*60)
    print("RETRY COMPLETE")
    print("="*60)
    
    # Reload progress
    with open(progress_file, "r") as f:
        app_results = json.load(f)
    
    total_samples = sum(r["samples"] for r in app_results.values())
    target_samples = sum(r["target"] for r in app_results.values())
    
    print(f"\nFinal Results:")
    print(f"  Total: {total_samples}/{target_samples} samples")
    print(f"  Success Rate: {(total_samples/target_samples*100):.1f}%")
    print(f"\nPer-App:")
    for app, result in sorted(app_results.items()):
        status = "✅" if result.get("completed") else "⚠️"
        print(f"  {status} {app}: {result['samples']}/{result['target']}")

if __name__ == "__main__":
    main()

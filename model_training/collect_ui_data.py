"""
UI Interaction Data Collector

Records UI interactions for training a vision model.
Captures screenshots + action sequences for fine-tuning.

Usage:
    python collect_ui_data.py
    
Then follow prompts to record interactions.
"""

import pyautogui
import time
import json
from pathlib import Path
from datetime import datetime
import sys

class UIDataCollector:
    """Collects UI interaction data for model training"""
    
    def __init__(self, output_dir="training_data"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load existing dataset or create new
        self.dataset_file = self.output_dir / "dataset.json"
        if self.dataset_file.exists():
            with open(self.dataset_file) as f:
                self.samples = json.load(f)
            print(f"📂 Loaded existing dataset with {len(self.samples)} samples")
        else:
            self.samples = []
            print("📝 Creating new dataset")
    
    def record_interaction(self):
        """Record a single UI interaction"""
        
        sample_id = len(self.samples)
        print(f"\n{'='*60}")
        print(f"Recording Sample #{sample_id + 1}")
        print(f"{'='*60}")
        
        # Get task description
        print("\n1️⃣  What task should be performed?")
        print("   Examples:")
        print("   - Lower brightness to 40%")
        print("   - Open Chrome browser")
        print("   - Increase volume to 75%")
        instruction = input("   Task: ").strip()
        
        if not instruction:
            print("❌ No instruction provided, skipping...")
            return False
        
        # Get action sequence
        print("\n2️⃣  What actions are needed? (Enter one per line, empty line to finish)")
        print("   Format: <type>|<target>|<value>")
        print("   Examples:")
        print("   - click|System")
        print("   - click|Display")
        print("   - set_slider|Brightness|40")
        print("   - type|search box|hello world")
        
        actions = []
        action_num = 1
        while True:
            action_str = input(f"   Action {action_num}: ").strip()
            if not action_str:
                break
            
            parts = action_str.split("|")
            if len(parts) < 2:
                print("   ⚠️  Invalid format, use: type|target or type|target|value")
                continue
            
            action = {
                "type": parts[0].strip(),
                "target": parts[1].strip()
            }
            if len(parts) >= 3:
                action["value"] = parts[2].strip()
            
            actions.append(action)
            action_num += 1
        
        if not actions:
            print("❌ No actions provided, skipping...")
            return False
        
        # Capture before screenshot
        print("\n3️⃣  Position your screen to the STARTING state")
        print("   (The state BEFORE performing any actions)")
        input("   Press Enter when ready...")
        
        print("   📸 Capturing screenshot in 3 seconds...")
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        before_image = f"sample_{sample_id:04d}_before.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(self.output_dir / before_image)
        print(f"   ✅ Saved {before_image}")
        
        # Capture after screenshot
        print("\n4️⃣  Now perform the task manually")
        print(f"   Task: {instruction}")
        print("   Actions to perform:")
        for i, action in enumerate(actions, 1):
            if "value" in action:
                print(f"   {i}. {action['type']} on '{action['target']}' with value '{action['value']}'")
            else:
                print(f"   {i}. {action['type']} on '{action['target']}'")
        input("\n   Press Enter when you've completed ALL actions...")
        
        print("   📸 Capturing final screenshot in 3 seconds...")
        for i in range(3, 0, -1):
            print(f"   {i}...")
            time.sleep(1)
        
        after_image = f"sample_{sample_id:04d}_after.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(self.output_dir / after_image)
        print(f"   ✅ Saved {after_image}")
        
        # Save sample metadata
        sample = {
            "id": sample_id,
            "timestamp": datetime.now().isoformat(),
            "instruction": instruction,
            "actions": actions,
            "before_image": before_image,
            "after_image": after_image,
        }
        
        self.samples.append(sample)
        self._save_dataset()
        
        print(f"\n✅ Sample #{sample_id + 1} saved successfully!")
        return True
    
    def _save_dataset(self):
        """Save dataset to JSON file"""
        with open(self.dataset_file, "w") as f:
            json.dump(self.samples, f, indent=2)
        print(f"💾 Dataset saved ({len(self.samples)} samples total)")
    
    def show_stats(self):
        """Display dataset statistics"""
        if not self.samples:
            print("\n📊 Dataset is empty")
            return
        
        print(f"\n📊 Dataset Statistics")
        print(f"{'='*60}")
        print(f"Total samples: {len(self.samples)}")
        
        # Count action types
        action_types = {}
        for sample in self.samples:
            for action in sample["actions"]:
                action_type = action["type"]
                action_types[action_type] = action_types.get(action_type, 0) + 1
        
        print(f"\nAction types:")
        for action_type, count in sorted(action_types.items()):
            print(f"  {action_type}: {count}")
        
        print(f"\nRecent samples:")
        for sample in self.samples[-5:]:
            print(f"  #{sample['id']}: {sample['instruction']}")
    
    def export_for_training(self):
        """Export dataset in training format"""
        if not self.samples:
            print("❌ No samples to export")
            return
        
        training_file = self.output_dir / "train.jsonl"
        
        with open(training_file, "w") as f:
            for sample in self.samples:
                # Format for Qwen-VL / LLaVA training
                example = {
                    "image": sample["before_image"],
                    "conversations": [
                        {
                            "from": "human",
                            "value": f"<image>\nTask: {sample['instruction']}\nWhat actions should I take to complete this task? Respond with a JSON array of actions."
                        },
                        {
                            "from": "gpt",
                            "value": json.dumps(sample["actions"], indent=2)
                        }
                    ]
                }
                f.write(json.dumps(example) + "\n")
        
        print(f"\n✅ Exported {len(self.samples)} samples to {training_file}")
        print(f"   This file is ready for fine-tuning!")

def main():
    """Main collection loop"""
    collector = UIDataCollector()
    
    print("\n🤖 UI Interaction Data Collector")
    print("="*60)
    print("This tool helps you collect training data for UI automation.")
    print("You'll record screenshots + action sequences for each task.")
    print("="*60)
    
    while True:
        print("\n📋 Menu:")
        print("  1. Record new interaction")
        print("  2. Show dataset statistics")
        print("  3. Export for training")
        print("  4. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "1":
            try:
                collector.record_interaction()
            except KeyboardInterrupt:
                print("\n⚠️  Recording cancelled")
            except Exception as e:
                print(f"\n❌ Error: {e}")
                import traceback
                traceback.print_exc()
        
        elif choice == "2":
            collector.show_stats()
        
        elif choice == "3":
            collector.export_for_training()
        
        elif choice == "4":
            print("\n👋 Goodbye!")
            collector.show_stats()
            break
        
        else:
            print("❌ Invalid choice")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)

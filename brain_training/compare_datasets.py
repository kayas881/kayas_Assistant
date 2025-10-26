"""
Quick comparison: Old vs Enhanced Dataset Quality
"""
import json
from pathlib import Path

print("=" * 80)
print("📊 DATASET QUALITY COMPARISON")
print("=" * 80)

# Load both datasets
old_path = Path("training_data/mega_brain_dataset_8000.jsonl")
enhanced_path = Path("training_data/mega_brain_dataset_8000_enhanced.jsonl")

def analyze_dataset(path):
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    
    # Count multi-turn
    multi_turn = sum(1 for d in data if len(d['messages']) > 3)
    
    # Count dynamic args (timestamps, dates)
    dynamic = sum(1 for d in data if any(m in str(d) for m in ['_202', 'backup_', 'logs/', 'archive/']))
    
    # Categories
    cats = {}
    for d in data:
        cat = d.get('category', 'unknown')
        cats[cat] = cats.get(cat, 0) + 1
    
    return {
        'total': len(data),
        'multi_turn': multi_turn,
        'multi_turn_pct': multi_turn / len(data) * 100,
        'dynamic': dynamic,
        'dynamic_pct': dynamic / len(data) * 100,
        'categories': cats,
        'clarification': cats.get('clarification', 0),
        'human_dialog': cats.get('human_dialog', 0),
    }

if old_path.exists() and enhanced_path.exists():
    print("\n📁 OLD DATASET (Template-based)")
    old = analyze_dataset(old_path)
    print(f"  Total examples: {old['total']}")
    print(f"  Multi-turn conversations: {old['multi_turn']} ({old['multi_turn_pct']:.1f}%)")
    print(f"  Dynamic arguments: {old['dynamic']} ({old['dynamic_pct']:.1f}%)")
    print(f"  Clarification examples: {old['clarification']} ({old['clarification']/old['total']*100:.1f}%)")
    print(f"  Human dialog: {old['human_dialog']} ({old['human_dialog']/old['total']*100:.1f}%)")
    print(f"  Unique categories: {len(old['categories'])}")
    
    print("\n✨ ENHANCED DATASET (Production-quality)")
    enhanced = analyze_dataset(enhanced_path)
    print(f"  Total examples: {enhanced['total']}")
    print(f"  Multi-turn conversations: {enhanced['multi_turn']} ({enhanced['multi_turn_pct']:.1f}%)")
    print(f"  Dynamic arguments: {enhanced['dynamic']} ({enhanced['dynamic_pct']:.1f}%)")
    print(f"  Clarification examples: {enhanced['clarification']} ({enhanced['clarification']/enhanced['total']*100:.1f}%)")
    print(f"  Human dialog: {enhanced['human_dialog']} ({enhanced['human_dialog']/enhanced['total']*100:.1f}%)")
    print(f"  Unique categories: {len(enhanced['categories'])}")
    
    print("\n📈 IMPROVEMENTS")
    print(f"  Multi-turn: {old['multi_turn']} → {enhanced['multi_turn']} (+{enhanced['multi_turn'] - old['multi_turn']})")
    print(f"  Dynamic args: {old['dynamic_pct']:.1f}% → {enhanced['dynamic_pct']:.1f}% (+{enhanced['dynamic_pct'] - old['dynamic_pct']:.1f}%)")
    print(f"  Clarification: {old['clarification']} → {enhanced['clarification']} (+{enhanced['clarification'] - old['clarification']})")
    print(f"  Human dialog: {old['human_dialog']} → {enhanced['human_dialog']} (+{enhanced['human_dialog'] - old['human_dialog']})")
    
    print("\n🎯 QUALITY SCORE")
    old_score = (old['multi_turn_pct'] + old['dynamic_pct'] + (old['clarification']/old['total']*100)) / 3
    enhanced_score = (enhanced['multi_turn_pct'] + enhanced['dynamic_pct'] + (enhanced['clarification']/enhanced['total']*100)) / 3
    print(f"  Old dataset: {old_score:.1f}/100")
    print(f"  Enhanced dataset: {enhanced_score:.1f}/100")
    print(f"  Improvement: +{enhanced_score - old_score:.1f} points")
    
else:
    print("\n⚠️ One or both datasets not found")
    if old_path.exists():
        print(f"  ✅ Found: {old_path}")
    else:
        print(f"  ❌ Missing: {old_path}")
    if enhanced_path.exists():
        print(f"  ✅ Found: {enhanced_path}")
    else:
        print(f"  ❌ Missing: {enhanced_path}")

print("\n" + "=" * 80)
print("✅ Analysis complete!")
print("=" * 80)

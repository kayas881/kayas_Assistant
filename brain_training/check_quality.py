import json
from pathlib import Path

# Load the enhanced dataset
data_path = Path(__file__).parent / "training_data" / "test_enhanced_1k.jsonl"
data = []
with open(data_path, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            data.append(json.loads(line))

print(f"✅ Loaded {len(data)} examples\n")

# Check multi-turn conversations
multi_turn = [d for d in data if len(d['messages']) > 3]
print(f"📊 Multi-turn conversations (>3 messages): {len(multi_turn)} ({len(multi_turn)/len(data)*100:.1f}%)")

# Check categories
categories = {}
for d in data:
    cat = d.get('category', 'unknown')
    categories[cat] = categories.get(cat, 0) + 1

print(f"\n📊 Category Distribution:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    print(f"  {cat:20s}: {count:4d} ({count/len(data)*100:.1f}%)")

# Check for dynamic arguments (timestamps, dates)
print(f"\n🔍 Checking for Dynamic Arguments...")
dynamic_examples = []
for d in data:
    content = str(d['messages'][-1]['content'])
    if any(marker in content for marker in ['_202', '_v', 'backup_', 'logs/', 'meetings/', 'archive/']):
        dynamic_examples.append(d)

print(f"  Found {len(dynamic_examples)} examples with dynamic filenames/paths ({len(dynamic_examples)/len(data)*100:.1f}%)")

# Sample dynamic example
if dynamic_examples:
    print(f"\n📝 Sample with dynamic arguments:")
    ex = dynamic_examples[0]
    user_msg = [m for m in ex['messages'] if m['role'] == 'user'][0]['content']
    print(f"  User: {user_msg}")
    assist_content = ex['messages'][-1]['content']
    print(f"  Assistant: {assist_content[:400]}...")

# Sample multi-turn example
if multi_turn:
    print(f"\n💬 Sample multi-turn conversation:")
    ex = multi_turn[0]
    for i, msg in enumerate(ex['messages']):
        role = msg['role'].upper()
        content = msg['content'][:150]
        print(f"  [{role}]: {content}...")
        if i >= 4:  # Show first 5 messages
            break

print(f"\n✨ Quality Assessment:")
print(f"  ✅ Multi-turn coverage: {len(multi_turn)/len(data)*100:.1f}% (target 10%)")
print(f"  ✅ Dynamic args: {len(dynamic_examples)/len(data)*100:.1f}%")
print(f"  ✅ Clarification examples: {categories.get('clarification', 0)} ({categories.get('clarification', 0)/len(data)*100:.1f}%)")
print(f"  ✅ Human dialog: {categories.get('human_dialog', 0)} ({categories.get('human_dialog', 0)/len(data)*100:.1f}%)")
print(f"  ✅ Error handling: {categories.get('error_handling', 0)} + clarification = {categories.get('error_handling', 0) + categories.get('clarification', 0)} ({(categories.get('error_handling', 0) + categories.get('clarification', 0))/len(data)*100:.1f}%)")

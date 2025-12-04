"""Quick script to check OCR quality in bboxes.json"""
import json
from pathlib import Path
from collections import Counter

data_dir = Path("training_data_auto")
bboxes_file = data_dir / "bboxes.json"

print("📊 Analyzing bbox quality...\n")

with open(bboxes_file) as f:
    bboxes = json.load(f)

# Stats
total_images = len(bboxes)
total_elements = sum(len(elems) for elems in bboxes.values())
elements_with_text = sum(1 for elems in bboxes.values() for e in elems if e.get('name', '').strip())
elements_from_ocr = sum(1 for elems in bboxes.values() for e in elems if e.get('confidence'))

print(f"Total images: {total_images:,}")
print(f"Total elements: {total_elements:,}")
print(f"Elements with text: {elements_with_text:,} ({elements_with_text/total_elements*100:.1f}%)")
print(f"Elements from OCR: {elements_from_ocr:,} ({elements_from_ocr/total_elements*100:.1f}%)")

# Sample a few images with good OCR
print("\n📸 Sample elements with OCR text:\n")
count = 0
for img_name, elements in list(bboxes.items())[:500]:
    text_elements = [e for e in elements if e.get('name', '').strip() and e.get('confidence', 0) > 0.5]
    if text_elements and count < 3:
        print(f"Image: {img_name}")
        for elem in text_elements[:10]:
            print(f"  • {elem['type']}: '{elem['name']}' (conf: {elem.get('confidence', 0):.2f})")
        print()
        count += 1

# Element types
print("📋 Element type distribution:")
type_counts = Counter()
for elements in bboxes.values():
    for e in elements:
        type_counts[e['type']] += 1

for elem_type, count in type_counts.most_common(10):
    print(f"  {elem_type}: {count:,}")

print("\n✅ Analysis complete!")

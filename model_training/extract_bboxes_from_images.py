"""
Extract UI elements and bounding boxes from existing screenshots using OCR and image analysis
Since we can't recreate the live UI state, we'll use computer vision to detect UI elements
"""
import json
from pathlib import Path
from PIL import Image
import pytesseract
import cv2
import numpy as np
from tqdm import tqdm
from datetime import datetime

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\KAYAS\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

def detect_ui_elements_from_image(image_path):
    """
    Detect UI elements from a screenshot using computer vision techniques
    Returns list of detected elements with bboxes
    """
    # Load image
    img = Image.open(image_path)
    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    elements = []
    
    # Method 1: Detect text regions using OCR
    try:
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        
        for i in range(len(ocr_data['text'])):
            text = ocr_data['text'][i].strip()
            conf = int(ocr_data['conf'][i])
            
            # Only include confident text detections
            if conf > 30 and len(text) > 0:
                x = ocr_data['left'][i]
                y = ocr_data['top'][i]
                w = ocr_data['width'][i]
                h = ocr_data['height'][i]
                
                # Determine element type based on characteristics
                if h < 40 and w < 200:
                    elem_type = "TextControl"
                elif "button" in text.lower() or h < 50:
                    elem_type = "ButtonControl"
                else:
                    elem_type = "TextControl"
                
                elements.append({
                    "type": elem_type,
                    "name": text,
                    "bbox": [x, y, x + w, y + h],
                    "confidence": conf / 100.0
                })
    except Exception as e:
        print(f"   OCR failed: {e}")
    
    # Method 2: Detect rectangular UI controls using edge detection
    edges = cv2.Canny(gray, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        
        # Filter for reasonable UI control sizes
        if 500 < area < 50000 and 10 < w < 800 and 10 < h < 600:
            # Classify based on aspect ratio
            aspect = w / h if h > 0 else 0
            
            if 2 < aspect < 10:
                elem_type = "SliderControl"
            elif 0.8 < aspect < 1.2:
                elem_type = "ButtonControl"
            else:
                elem_type = "WindowControl"
            
            elements.append({
                "type": elem_type,
                "name": "",
                "bbox": [x, y, x + w, y + h],
                "detection_method": "edge_detection"
            })
    
    # Remove duplicate/overlapping elements
    elements = remove_overlaps(elements)
    
    return elements

def remove_overlaps(elements, iou_threshold=0.7):
    """Remove highly overlapping bounding boxes"""
    if len(elements) <= 1:
        return elements
    
    # Sort by confidence if available, otherwise by area
    elements = sorted(elements, 
                     key=lambda x: x.get('confidence', 0) + (x['bbox'][2]-x['bbox'][0])*(x['bbox'][3]-x['bbox'][1])/10000,
                     reverse=True)
    
    keep = []
    for elem in elements:
        bbox1 = elem['bbox']
        
        # Check overlap with kept elements
        overlap = False
        for kept_elem in keep:
            bbox2 = kept_elem['bbox']
            if compute_iou(bbox1, bbox2) > iou_threshold:
                overlap = True
                break
        
        if not overlap:
            keep.append(elem)
    
    return keep

def compute_iou(box1, box2):
    """Compute Intersection over Union of two bounding boxes"""
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2
    
    # Intersection
    xi_min = max(x1_min, x2_min)
    yi_min = max(y1_min, y2_min)
    xi_max = min(x1_max, x2_max)
    yi_max = min(y1_max, y2_max)
    
    if xi_max <= xi_min or yi_max <= yi_min:
        return 0.0
    
    intersection = (xi_max - xi_min) * (yi_max - yi_min)
    
    # Union
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    union = area1 + area2 - intersection
    
    return intersection / union if union > 0 else 0.0

def extract_all_bboxes():
    """Extract bboxes from all screenshots"""
    
    # Use absolute path
    script_dir = Path(__file__).parent
    data_dir = script_dir / "training_data_auto"
    
    if not data_dir.exists():
        print(f"❌ Directory not found: {data_dir}")
        return
    
    # Load existing bboxes
    bboxes_file = data_dir / "bboxes.json"
    existing_bboxes = {}
    
    if bboxes_file.exists():
        print("📦 Loading existing bboxes.json...")
        with open(bboxes_file) as f:
            existing_bboxes = json.load(f)
        print(f"   Found {len(existing_bboxes)} existing entries")
    
    # Find all screenshots
    print("\n🔍 Finding all frame_*.png files...")
    frame_files = sorted(data_dir.glob("frame_*.png"))
    print(f"   Found {len(frame_files)} screenshot files")
    
    if len(frame_files) == 0:
        print("❌ No frame_*.png files found!")
        return
    
    # Filter to only process new images
    to_process = [f for f in frame_files if f.name not in existing_bboxes]
    print(f"   Processing {len(to_process)} new screenshots (skipping {len(existing_bboxes)} existing)")
    
    if len(to_process) == 0:
        print("\n✅ All screenshots already have bbox data!")
        return
    
    # Check for tesseract
    try:
        pytesseract.get_tesseract_version()
        print("✅ Tesseract OCR found")
    except:
        print("⚠️  Tesseract not found - will use edge detection only")
        print("   Install: https://github.com/UB-Mannheim/tesseract/wiki")
    
    # Process images
    print(f"\n🔨 Extracting UI elements from {len(to_process)} screenshots...")
    print("   This may take 15-30 minutes...")
    
    new_bboxes = {}
    errors = []
    
    for img_path in tqdm(to_process, desc="Processing"):
        try:
            elements = detect_ui_elements_from_image(img_path)
            new_bboxes[img_path.name] = elements
        except Exception as e:
            errors.append((img_path.name, str(e)))
    
    # Merge with existing
    all_bboxes = {**existing_bboxes, **new_bboxes}
    
    # Save updated bboxes
    print(f"\n💾 Saving to {bboxes_file}...")
    with open(bboxes_file, 'w') as f:
        json.dump(all_bboxes, f, indent=2)
    
    # Statistics
    total_elements = sum(len(elems) for elems in all_bboxes.values())
    avg_elements = total_elements / len(all_bboxes) if all_bboxes else 0
    
    print(f"\n✅ Extraction complete!")
    print(f"   Total images with bboxes: {len(all_bboxes):,}")
    print(f"   New images processed: {len(new_bboxes):,}")
    print(f"   Total UI elements detected: {total_elements:,}")
    print(f"   Average elements per image: {avg_elements:.1f}")
    print(f"   File size: {bboxes_file.stat().st_size / 1024 / 1024:.2f} MB")
    
    if errors:
        print(f"\n⚠️  Errors: {len(errors)}")
        for img, err in errors[:5]:
            print(f"   {img}: {err}")
    
    # Now rebuild dataset.json
    print(f"\n🔄 Rebuilding dataset.json with updated bboxes...")
    import subprocess
    subprocess.run(["python", "rebuild_dataset.py"], cwd=data_dir.parent)

if __name__ == "__main__":
    print("="*70)
    print("  UI Element & BBox Extractor")
    print("  Uses OCR + Edge Detection to analyze screenshots")
    print("="*70 + "\n")
    
    extract_all_bboxes()
    
    print("\n🎉 Done! Your dataset is ready for training!")

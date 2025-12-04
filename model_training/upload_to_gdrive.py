"""
Upload training dataset to Google Drive

SIMPLER APPROACH: Use Google Drive Desktop App or Manual Upload

Since PyDrive2 requires OAuth setup, we recommend:
1. Install Google Drive Desktop App (easier)
2. Or use this script to prepare a ZIP file for manual upload

Requirements:
    pip install tqdm

Usage:
    python upload_to_gdrive.py
"""

from pathlib import Path
import zipfile
import os
import sys
from tqdm import tqdm

def authenticate_gdrive():
    """Show instructions for Google Drive Desktop"""
    print("="*70)
    print(" "*15 + "GOOGLE DRIVE UPLOAD OPTIONS")
    print("="*70 + "\n")
    
    print("Choose your preferred upload method:\n")
    print("Option 1: Google Drive Desktop App (RECOMMENDED)")
    print("-" * 70)
    print("  1. Download: https://www.google.com/drive/download/")
    print("  2. Install and sign in with your Google account")
    print("  3. Copy training_data_auto folder to 'Google Drive' folder")
    print("  4. It will auto-sync to cloud (no manual upload needed!)")
    print("\n")
    
    print("Option 2: Manual Web Upload")
    print("-" * 70)
    print("  1. This script will create training_data.zip")
    print("  2. Go to: https://drive.google.com/")
    print("  3. Click 'New' → 'File upload'")
    print("  4. Select training_data.zip")
    print("  5. Extract in Colab after upload")
    print("\n")
    
    print("Option 3: Colab Direct Upload (SLOWEST)")
    print("-" * 70)
    print("  1. Skip this script")
    print("  2. In Colab, use: files.upload() to upload train.jsonl")
    print("  3. Upload screenshots folder separately")
    print("\n")
    
    choice = input("Enter choice (1/2/3) or 'q' to quit: ").strip()
    
    if choice == '1':
        return 'desktop'
    elif choice == '2':
        return 'zip'
    elif choice == '3':
        return 'colab'
    else:
        print("\n❌ Cancelled")
        return None


def create_zip_file(source_folder, output_file):
    """Create a ZIP file of the training data"""
    source_path = Path(source_folder)
    
    if not source_path.exists():
        print(f"❌ Error: Folder not found: {source_path}")
        return False
    
    # Get all files
    all_files = list(source_path.glob('**/*'))
    files_to_zip = [f for f in all_files if f.is_file()]
    
    print(f"\n� Creating ZIP archive...")
    print(f"   Source: {source_path}")
    print(f"   Files: {len(files_to_zip):,}")
    print(f"   Output: {output_file}\n")
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in files_to_zip)
    print(f"   Uncompressed size: {total_size / (1024**3):.2f} GB")
    print(f"   This may take 5-10 minutes...\n")
    
    # Create ZIP with progress bar
    with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED, compresslevel=5) as zipf:
        with tqdm(total=len(files_to_zip), unit='file') as pbar:
            for file_path in files_to_zip:
                arcname = file_path.relative_to(source_path.parent)
                zipf.write(file_path, arcname)
                pbar.update(1)
    
    # Check final size
    zip_size = Path(output_file).stat().st_size
    compression_ratio = (1 - zip_size / total_size) * 100
    
    print(f"\n✅ ZIP file created successfully!")
    print(f"   Size: {zip_size / (1024**3):.2f} GB")
    print(f"   Compression: {compression_ratio:.1f}%")
    print(f"   Location: {output_file}\n")
    
    return True

def show_desktop_instructions():
    """Show instructions for Google Drive Desktop"""
    print("\n" + "="*70)
    print("📱 GOOGLE DRIVE DESKTOP - NEXT STEPS")
    print("="*70)
    print("\n1. Download & Install Google Drive Desktop:")
    print("   → https://www.google.com/drive/download/")
    print("\n2. Sign in with your Google account")
    print("\n3. After installation, you'll see 'Google Drive' in File Explorer")
    print("\n4. Copy the entire folder:")
    print("   FROM: C:\\Users\\KAYAS\\Desktop\\kayasWorkPlace\\kayas\\model_training\\training_data_auto")
    print("   TO:   G:\\My Drive\\training_data_auto")
    print("      (or wherever your Google Drive folder is mounted)")
    print("\n5. Wait for sync to complete (check for green checkmarks)")
    print("\n6. In Google Colab, access your data at:")
    print("   /content/drive/MyDrive/training_data_auto/")
    print("\n" + "="*70)
    print("✅ This is the EASIEST and MOST RELIABLE method!")
    print("="*70 + "\n")

def show_zip_upload_instructions(zip_file):
    """Show instructions for manual ZIP upload"""
    print("\n" + "="*70)
    print("📤 MANUAL UPLOAD - NEXT STEPS")
    print("="*70)
    print(f"\n1. Your ZIP file is ready: {zip_file}")
    print("\n2. Go to: https://drive.google.com/")
    print("\n3. Click 'New' → 'File upload'")
    print("\n4. Select the ZIP file and wait for upload")
    print("   (This may take 30-60 minutes depending on your internet)")
    print("\n5. In Google Colab, extract the ZIP:")
    print("""
   from google.colab import drive
   drive.mount('/content/drive')
   
   import zipfile
   zip_path = '/content/drive/MyDrive/training_data.zip'
   extract_to = '/content/'
   
   with zipfile.ZipFile(zip_path, 'r') as zip_ref:
       zip_ref.extractall(extract_to)
   
   # Data will be at: /content/training_data_auto/
""")
    print("="*70 + "\n")

def show_colab_upload_instructions():
    """Show instructions for Colab direct upload"""
    print("\n" + "="*70)
    print("☁️  COLAB DIRECT UPLOAD - NEXT STEPS")
    print("="*70)
    print("\n⚠️  WARNING: This is SLOW and may timeout for large datasets!")
    print("   Recommended only if other methods don't work.\n")
    print("In your Colab notebook, use:")
    print("""
from google.colab import files
import zipfile
from pathlib import Path

# Option A: Upload ZIP file
uploaded = files.upload()  # Select training_data.zip
zip_name = list(uploaded.keys())[0]

with zipfile.ZipFile(zip_name, 'r') as zip_ref:
    zip_ref.extractall('/content/')

# Option B: Upload folder to mounted Drive
from google.colab import drive
drive.mount('/content/drive')

# Then manually upload via Drive web interface
""")
    print("="*70 + "\n")


def main():
    print("="*70)
    print(" "*15 + "GOOGLE DRIVE UPLOAD HELPER")
    print("="*70 + "\n")
    
    # Get upload method choice
    method = authenticate_gdrive()
    
    if not method:
        return
    
    # Check if training data exists
    data_folder = Path("training_data_auto")
    
    if not data_folder.exists():
        print(f"\n❌ Training data folder not found: {data_folder}")
        print("Make sure you're in the model_training directory")
        return
    
    # Execute based on chosen method
    if method == 'desktop':
        show_desktop_instructions()
        
    elif method == 'zip':
        # Create ZIP file
        zip_file = "training_data.zip"
        
        # Check disk space
        import shutil
        free_space = shutil.disk_usage('.').free
        needed_space = sum(f.stat().st_size for f in data_folder.glob('**/*') if f.is_file())
        
        if free_space < needed_space:
            print(f"\n❌ Not enough disk space!")
            print(f"   Available: {free_space / (1024**3):.2f} GB")
            print(f"   Needed: {needed_space / (1024**3):.2f} GB")
            print("\n💡 Solution: Use Google Drive Desktop instead (Option 1)")
            return
        
        success = create_zip_file(data_folder, zip_file)
        
        if success:
            show_zip_upload_instructions(zip_file)
            
    elif method == 'colab':
        show_colab_upload_instructions()
    
    print("\n💡 RECOMMENDATION:")
    print("   → Use Google Drive Desktop (Option 1) for best experience!")
    print("   → It's faster, more reliable, and easier to use\n")

if __name__ == "__main__":
    main()

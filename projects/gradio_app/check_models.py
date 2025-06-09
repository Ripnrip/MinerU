#!/usr/bin/env python3
"""
MinerU Model Checker and Fixer
Checks for missing model files and creates necessary symlinks
"""

import os
import sys
from pathlib import Path

def check_and_fix_models():
    """Check for missing model files and create symlinks if needed"""
    
    print("🔍 Checking MinerU model files...")
    
    # Base model directory
    base_dir = Path.home() / ".cache/huggingface/hub/models--opendatalab--PDF-Extract-Kit-1.0/snapshots"
    
    # Find the snapshot directory (it has a long hash name)
    snapshot_dirs = [d for d in base_dir.glob("*") if d.is_dir()]
    
    if not snapshot_dirs:
        print("❌ No PDF-Extract-Kit model snapshots found!")
        print("💡 Please run: magic-pdf --help to trigger model download")
        return False
    
    snapshot_dir = snapshot_dirs[0]  # Use the first (should be only one)
    
    print(f"📂 Found model snapshot: {snapshot_dir.name}")
    
    # Check OCR models
    ocr_dir = snapshot_dir / "models/OCR/paddleocr_torch"
    
    if not ocr_dir.exists():
        print("❌ OCR model directory not found!")
        return False
    
    print(f"📁 OCR directory: {ocr_dir}")
    
    # Required OCR model files
    required_files = [
        "en_PP-OCRv3_det_infer.pth",
        "en_PP-OCRv4_rec_server_doc_infer.pth"
    ]
    
    fallback_files = [
        "ch_PP-OCRv3_det_infer.pth", 
        "ch_PP-OCRv4_rec_server_doc_infer.pth"
    ]
    
    fixes_applied = 0
    
    for i, required_file in enumerate(required_files):
        required_path = ocr_dir / required_file
        fallback_path = ocr_dir / fallback_files[i]
        
        if required_path.exists():
            print(f"✅ {required_file} - Found")
        elif fallback_path.exists():
            print(f"🔧 {required_file} - Missing, creating symlink from {fallback_files[i]}")
            try:
                required_path.symlink_to(fallback_files[i])
                print(f"✅ Created symlink: {required_file} -> {fallback_files[i]}")
                fixes_applied += 1
            except Exception as e:
                print(f"❌ Failed to create symlink: {e}")
        else:
            print(f"❌ {required_file} - Missing (no fallback available)")
    
    if fixes_applied > 0:
        print(f"🔧 Applied {fixes_applied} fixes")
    
    print("✅ Model check complete!")
    return True

def check_environment():
    """Check if we're in the correct conda environment"""
    try:
        import magic_pdf
        print("✅ magic-pdf package found")
        return True
    except ImportError:
        print("❌ magic-pdf package not found")
        print("💡 Make sure you're in the MinerU-312 conda environment")
        return False

if __name__ == "__main__":
    print("🚀 MinerU Model Checker")
    print("=" * 50)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Check and fix models
    if not check_and_fix_models():
        sys.exit(1)
    
    print("\n🎉 All checks passed! MinerU should work correctly now.") 
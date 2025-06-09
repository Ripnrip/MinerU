#!/usr/bin/env python3
"""
Simple launcher for MinerU Gradio UI
This script handles environment setup and launches the enhanced Gradio interface.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_dependencies():
    """Check if required packages are installed."""
    try:
        import gradio
        import magic_pdf
        print("✅ Dependencies check passed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please make sure you're in the magicpdf310 conda environment")
        return False

def main():
    print("🚀 Starting MinerU Gradio UI...")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path(__file__).parent
    app_file = current_dir / "app_enhanced.py"
    
    if not app_file.exists():
        print("❌ Enhanced app file not found!")
        print(f"Expected: {app_file}")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        print("\n💡 To fix this, run:")
        print("conda activate magicpdf310")
        return 1
    
    # Change to the app directory
    os.chdir(current_dir)
    
    print("📂 Working directory:", current_dir)
    print("🎯 Launching enhanced Gradio interface...")
    print("🌐 The UI will be available at: http://localhost:7860")
    print("=" * 50)
    
    try:
        # Run the enhanced app
        subprocess.run([sys.executable, "app_enhanced.py"], check=True)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
        return 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running the app: {e}")
        return 1
    except FileNotFoundError:
        print("❌ Python interpreter not found!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
#!/usr/bin/env python3
"""
Run the Apple OCR backend server with Apple Silicon MPS optimization.

This script sets up the environment for optimal performance on Apple Silicon Macs
and starts the FastAPI server.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def setup_apple_silicon_env():
    """Set up environment variables for Apple Silicon optimization."""
    print("Setting up Apple Silicon environment...")
    
    # Set MPS memory management
    os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
    print("✅ Set PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0")
    
    # Set OCR batch size for MPS
    os.environ["OCR_BATCH_SIZE"] = "4"
    print("✅ Set OCR_BATCH_SIZE=4")
    
    # Optional: Force CPU mode (uncomment if needed)
    # os.environ["FORCE_CPU"] = "1"
    # print("⚠️ Forced CPU mode")
    
    print("Environment setup complete!")

def check_mps_availability():
    """Check if MPS is available."""
    try:
        import torch
        has_mps = hasattr(torch.backends, "mps")
        mps_available = torch.backends.mps.is_available() if has_mps else False
        mps_built = torch.backends.mps.is_built() if has_mps else False
        
        if mps_available and mps_built:
            print("✅ Apple Silicon MPS is available")
            return True
        else:
            print("⚠️ Apple Silicon MPS is not available")
            return False
    except ImportError:
        print("❌ PyTorch not installed")
        return False

def main():
    parser = argparse.ArgumentParser(description="Run Apple OCR server with Apple Silicon optimization")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", default="8000", type=int, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--force-cpu", action="store_true", help="Force CPU mode")
    parser.add_argument("--check-only", action="store_true", help="Only check MPS availability")
    
    args = parser.parse_args()
    
    print("Apple Silicon OCR Server")
    print("=" * 40)
    
    # Check MPS availability
    mps_available = check_mps_availability()
    
    if args.check_only:
        if mps_available:
            print("\n🎉 Apple Silicon MPS is ready to use!")
        else:
            print("\n⚠️ Apple Silicon MPS is not available, will use CPU")
        return
    
    # Set up environment
    setup_apple_silicon_env()
    
    # Force CPU mode if requested
    if args.force_cpu:
        os.environ["FORCE_CPU"] = "1"
        print("⚠️ Forced CPU mode")
    
    # Build uvicorn command
    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", args.host,
        "--port", str(args.port)
    ]
    
    if args.reload:
        cmd.append("--reload")
        print("✅ Auto-reload enabled")
    
    print(f"\nStarting server on {args.host}:{args.port}")
    print(f"Command: {' '.join(cmd)}")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 40)
    
    try:
        # Start the server
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

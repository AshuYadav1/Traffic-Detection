#!/usr/bin/env python3
"""
Test script to verify the Traffic Violation Detection API setup
"""

import sys
import os
from pathlib import Path

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        import fastapi
        print("✅ FastAPI imported successfully")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn imported successfully")
    except ImportError as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False
    
    try:
        import cv2
        print("✅ OpenCV imported successfully")
    except ImportError as e:
        print(f"❌ OpenCV import failed: {e}")
        return False
    
    try:
        from ultralytics import YOLO
        print("✅ YOLO imported successfully")
    except ImportError as e:
        print(f"❌ YOLO import failed: {e}")
        return False
    
    try:
        import torch
        print("✅ PyTorch imported successfully")
    except ImportError as e:
        print(f"❌ PyTorch import failed: {e}")
        return False
    
    try:
        import sklearn
        print("✅ Scikit-learn imported successfully")
    except ImportError as e:
        print(f"❌ Scikit-learn import failed: {e}")
        return False
    
    return True

def test_app_structure():
    """Test if the app structure is correct"""
    print("\n🏗️  Testing app structure...")
    
    required_files = [
        "app/__init__.py",
        "app/main.py",
        "app/core/config.py",
        "app/core/database.py",
        "app/services/violation_processor.py",
        "app/api/v1/api.py",
        "app/api/v1/endpoints/videos.py",
        "app/api/v1/endpoints/violations.py",
        "app/api/v1/endpoints/jobs.py",
        "app/schemas/video.py",
        "app/schemas/violation.py",
        "app/schemas/job.py"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return False
    else:
        print("✅ All required files present")
        return True

def test_model_files():
    """Test if model files are present"""
    print("\n🤖 Testing model files...")
    
    model_files = ["svm_model.pkl", "pca.pkl"]
    missing_models = []
    
    for model in model_files:
        model_path = f"models/{model}"
        if os.path.exists(model_path):
            print(f"✅ {model} found")
        else:
            print(f"⚠️  {model} not found")
            missing_models.append(model)
    
    if missing_models:
        print(f"⚠️  Warning: Missing model files: {missing_models}")
        print("   The API will start but helmet detection may not work properly.")
    
    return True

def test_directories():
    """Test if required directories exist or can be created"""
    print("\n📁 Testing directories...")
    
    directories = ["uploads", "evidence", "models"]
    
    for directory in directories:
        try:
            os.makedirs(directory, exist_ok=True)
            print(f"✅ {directory}/ directory ready")
        except Exception as e:
            print(f"❌ Failed to create {directory}/: {e}")
            return False
    
    return True

def main():
    """Main test function"""
    print("🚀 Traffic Violation Detection API - Setup Test")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_imports),
        ("App Structure Test", test_app_structure),
        ("Model Files Test", test_model_files),
        ("Directories Test", test_directories)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The API is ready to run.")
        print("\n🚀 To start the API, run:")
        print("   python run.py")
        print("   or")
        print("   uvicorn app.main:app --host 0.0.0.0 --port 8000")
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

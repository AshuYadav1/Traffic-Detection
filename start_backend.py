#!/usr/bin/env python3
"""
Start the Traffic Violation Detection Backend API
"""

import subprocess
import sys
import os
import time
import requests
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'fastapi', 'uvicorn', 'torch', 'ultralytics', 
        'opencv-python', 'sqlalchemy', 'joblib', 'scikit-learn'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        for package in missing_packages:
            try:
                subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])
                print(f"✅ Installed {package}")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {package}")
                return False
    
    return True

def check_model_files():
    """Check if model files exist"""
    print("\n🤖 Checking model files...")
    
    model_files = {
        'YOLO': 'models/yolov8s.pt',
        'SVM': 'models/svm_model.pkl',
        'PCA': 'models/pca.pkl'
    }
    
    for name, path in model_files.items():
        if os.path.exists(path):
            print(f"✅ {name} model found: {path}")
        else:
            print(f"⚠️ {name} model not found: {path}")
            if name == 'YOLO':
                print("   YOLO model will be downloaded automatically")
            else:
                print("   Helmet detection will be limited without these models")

def start_backend():
    """Start the backend server"""
    print("\n🚀 Starting Traffic Violation Detection API...")
    
    try:
        # Start the server
        process = subprocess.Popen([
            sys.executable, '-m', 'uvicorn', 
            'app.main:app', 
            '--host', '0.0.0.0', 
            '--port', '8000',
            '--reload'
        ])
        
        print("✅ Backend server started!")
        print("📡 API available at: http://localhost:8000")
        print("📚 API docs at: http://localhost:8000/docs")
        print("🔍 Health check at: http://localhost:8000/health")
        print("\n⏳ Waiting for server to be ready...")
        
        # Wait for server to be ready
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get('http://localhost:8000/health', timeout=2)
                if response.status_code == 200:
                    print("✅ Server is ready!")
                    break
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print(f"⏳ Attempt {attempt + 1}/{max_attempts}...")
        else:
            print("❌ Server failed to start properly")
            return False
        
        print("\n🎉 Backend is running successfully!")
        print("\n📋 Next steps:")
        print("1. Open your Flutter admin dashboard")
        print("2. Navigate to the Upload section")
        print("3. Upload a video file")
        print("4. Watch real-time processing updates")
        print("5. View the processed video with violations highlighted")
        
        print("\n🛑 Press Ctrl+C to stop the server")
        
        # Keep the process running
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping server...")
            process.terminate()
            process.wait()
            print("✅ Server stopped")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        return False

def main():
    """Main function"""
    print("🚀 Traffic Violation Detection Backend Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('app/main.py'):
        print("❌ Error: Please run this script from the BACKEND directory")
        print("   Current directory:", os.getcwd())
        print("   Expected files: app/main.py")
        return 1
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Dependency check failed")
        return 1
    
    # Check model files
    check_model_files()
    
    # Start backend
    if not start_backend():
        print("❌ Failed to start backend")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Startup script for Traffic Violation Detection API
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def main():
    """Main startup function"""
    print("🚀 Starting Traffic Violation Detection API...")
    
    # Create necessary directories
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("evidence", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    # Check for required model files
    required_models = ["svm_model.pkl", "pca.pkl"]
    missing_models = []
    
    for model in required_models:
        model_path = f"models/{model}"
        if not os.path.exists(model_path):
            missing_models.append(model)
    
    if missing_models:
        print(f"⚠️  Warning: Missing model files: {', '.join(missing_models)}")
        print("   The API will start but helmet detection may not work properly.")
        print("   Please ensure these files are in the models/ directory.")
    
    # Start the server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()

#!/bin/bash

# Render Deployment Startup Script for Traffic Violation Detection API
echo "🚀 Starting Traffic Violation Detection API on Render..."

# Create necessary directories
mkdir -p /tmp/uploads
mkdir -p /tmp/evidence
mkdir -p models

# Set environment variables for Render deployment
export UPLOAD_DIR="/tmp/uploads"
export EVIDENCE_DIR="/tmp/evidence"

# Download YOLO model if not present (only small model for free tier)
if [ ! -f "models/yolov8s.pt" ]; then
    echo "📥 Downloading YOLO model..."
    python -c "
from ultralytics import YOLO
import os
os.makedirs('models', exist_ok=True)
model = YOLO('yolov8s.pt')
model.save('models/yolov8s.pt')
print('✅ YOLO model downloaded successfully')
"
fi

# Check if required model files exist
echo "🔍 Checking model files..."
if [ -f "models/svm_model.pkl" ]; then
    echo "✅ SVM model found"
else
    echo "⚠️  SVM model not found - helmet detection will be limited"
fi

if [ -f "models/pca.pkl" ]; then
    echo "✅ PCA model found"
else
    echo "⚠️  PCA model not found - helmet detection will be limited"
fi

# Run database migrations if needed
echo "🗄️  Setting up database..."
python -c "
from app.core.database import engine, Base
Base.metadata.create_all(bind=engine)
print('✅ Database tables created successfully')
" || echo "⚠️  Database setup had issues, but continuing..."

# Start the FastAPI application
echo "🌐 Starting FastAPI server on port ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1

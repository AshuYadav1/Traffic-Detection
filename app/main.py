"""
Traffic Violation Detection API
Main FastAPI application entry point
"""

# Import PIL compatibility patch first
from app.core.pil_compatibility import *

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.database import engine, Base
from app.services.violation_processor import ViolationProcessor
from app.websocket.connection_manager import ConnectionManager

# Create database tables
Base.metadata.create_all(bind=engine)

# Initialize violation processor
violation_processor = ViolationProcessor()

# Initialize WebSocket connection manager
connection_manager = ConnectionManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting Traffic Violation Detection API...")
    print(f"📁 Upload directory: {settings.UPLOAD_DIR}")
    print(f"📁 Evidence directory: {settings.EVIDENCE_DIR}")
    
    # Create necessary directories
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Traffic Violation Detection API...")

app = FastAPI(
    title="Traffic Violation Detection API",
    description="AI-powered traffic violation detection system with real-time processing",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api/v1")

# Mount static files for serving evidence images
app.mount("/evidence", StaticFiles(directory=settings.EVIDENCE_DIR), name="evidence")

# Mount static files for serving uploaded videos and citizen report attachments
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

@app.get("/")
async def root():
    return {
        "message": "Traffic Violation Detection API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

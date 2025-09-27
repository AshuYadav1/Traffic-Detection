"""
Application configuration settings
"""

import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Traffic Violation Detection API"
    
    # Base directory for the project
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # CORS Settings - Allow all origins for development
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # File Upload Settings
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "uploads")
    EVIDENCE_DIR: str = os.getenv("EVIDENCE_DIR", "evidence")
    MAX_FILE_SIZE: int = 500 * 1024 * 1024  # 500MB
    ALLOWED_VIDEO_TYPES: List[str] = ["video/mp4", "video/avi", "video/mov", "video/mkv"]
    
    # Model Settings
    MODEL_SIZE: str = "small"
    YOLO_MODEL_PATH: str = "models/yolov8s.pt"
    SVM_MODEL_PATH: str = "models/svm_model.pkl"
    PCA_MODEL_PATH: str = "models/pca.pkl"
    
    # Database Settings
    DATABASE_URL: str = "sqlite:///./traffic_violations.db"
    
    # Redis Settings (for caching and task queue)
    REDIS_URL: str = "redis://localhost:6379"
    
    # Processing Settings
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.5
    DEFAULT_IOU_THRESHOLD: float = 0.45
    MIN_MOTORCYCLE_AREA: int = 3000
    HELMET_CHECK_CONFIDENCE: float = 0.6
    
    # Traffic Direction Settings
    DEFAULT_TRAFFIC_DIRECTION: str = "right"  # 'left', 'right', 'up', 'down'
    
    # WebSocket Settings
    WEBSOCKET_HEARTBEAT_INTERVAL: int = 30
    
    class Config:
        env_file = ".env"

settings = Settings()

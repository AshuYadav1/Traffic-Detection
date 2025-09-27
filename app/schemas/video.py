"""
Video-related Pydantic schemas
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VideoUploadResponse(BaseModel):
    job_id: str
    status: str
    message: str
    input_filename: str
    file_size: int

class VideoProcessingRequest(BaseModel):
    traffic_direction: str = "right"
    confidence_threshold: float = 0.5
    min_motorcycle_area: int = 3000
    helmet_check_confidence: float = 0.6

class VideoProcessingResponse(BaseModel):
    job_id: str
    status: str
    total_violations: int
    red_light_violations: int
    helmet_violations: int
    wrong_way_violations: int
    processing_time: float
    output_video_url: Optional[str] = None

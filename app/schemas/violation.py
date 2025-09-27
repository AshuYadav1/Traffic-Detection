"""
Violation-related Pydantic schemas
"""

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ViolationResponse(BaseModel):
    id: int
    violation_type: str
    vehicle_type: Optional[str]
    tracker_id: Optional[int]
    confidence: float
    frame_number: int
    timestamp: datetime
    location: Optional[str]
    jurisdiction: Optional[str]
    evidence_image_path: Optional[str]
    evidence_video_path: Optional[str]
    processing_time: Optional[float]
    video_duration: Optional[float]
    violation_coordinates: Optional[str]
    is_verified: bool
    is_processed: bool
    notes: Optional[str]
    job_id: Optional[int]

    class Config:
        from_attributes = True

class ViolationStats(BaseModel):
    total_violations: int
    red_light_violations: int
    helmet_violations: int
    wrong_way_violations: int
    vehicle_type_stats: Dict[str, int]
    daily_violations: Dict[str, int]
    period_days: int

class ViolationCreate(BaseModel):
    violation_type: str
    vehicle_type: str
    tracker_id: int
    confidence: float
    frame_number: int
    evidence_image_path: str
    violation_coordinates: str
    job_id: int

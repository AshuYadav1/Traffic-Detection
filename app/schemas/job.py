"""
Job-related Pydantic schemas
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class JobResponse(BaseModel):
    id: int
    job_id: str
    video_path: str
    status: str
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    traffic_direction: str
    confidence_threshold: float
    min_motorcycle_area: int
    total_violations: int
    red_light_violations: int
    helmet_violations: int
    wrong_way_violations: int
    error_message: Optional[str]

    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    jobs: List[JobResponse]
    total: int
    skip: int
    limit: int

class JobCreate(BaseModel):
    video_path: str
    traffic_direction: str = "right"
    confidence_threshold: float = 0.5
    min_motorcycle_area: int = 3000

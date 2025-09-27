"""
Citizen Report schemas
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CitizenReportCreate(BaseModel):
    incident_type: str
    priority: str
    description: str
    vehicle_number: Optional[str] = None
    reporter_name: str
    reporter_phone: str
    latitude: float
    longitude: float
    location: str

class CitizenReportResponse(BaseModel):
    report_id: str
    incident_type: str
    priority: str
    description: str
    status: str
    created_at: str
    assigned_officer: Optional[str] = None
    message: Optional[str] = None
    attachment_paths: Optional[List[str]] = None
    reporter_name: Optional[str] = None
    reporter_phone: Optional[str] = None
    location: Optional[str] = None
    vehicle_number: Optional[str] = None

class CitizenReportUpdate(BaseModel):
    status: str
    feedback: Optional[str] = None

class CitizenReportAssignment(BaseModel):
    officer_id: int

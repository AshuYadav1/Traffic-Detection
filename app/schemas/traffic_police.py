"""
Traffic Police Pydantic schemas
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime

class TrafficPoliceBase(BaseModel):
    name: str
    email: EmailStr
    badge_number: str
    profile_image: Optional[str] = None
    assigned_area: Dict[str, Any]
    rto_office_id: int

class TrafficPoliceCreate(TrafficPoliceBase):
    password: str

class TrafficPoliceUpdate(BaseModel):
    name: Optional[str] = None
    badge_number: Optional[str] = None
    profile_image: Optional[str] = None
    assigned_area: Optional[Dict[str, Any]] = None
    rto_office_id: Optional[int] = None

class TrafficPoliceResponse(TrafficPoliceBase):
    id: int
    employee_id: str
    status: str
    created_at: str
    
    class Config:
        from_attributes = True

class TrafficPoliceLogin(BaseModel):
    email: EmailStr
    password: str

class EChallanBase(BaseModel):
    traffic_police_id: int
    violation_id: Optional[int] = None
    vehicle_number: str
    violation_type: str
    fine_amount: float
    location: Dict[str, Any]
    description: Optional[str] = None

class EChallanCreate(EChallanBase):
    pass

class EChallanResponse(EChallanBase):
    id: int
    challan_number: str
    status: str
    created_at: str
    due_date: str
    
    class Config:
        from_attributes = True

class ViolationAlert(BaseModel):
    id: str
    violation_type: str
    vehicle_number: str
    location: Dict[str, Any]
    timestamp: str
    confidence: float
    evidence_image: str
    status: str
    assigned_area: str

class PoliceStats(BaseModel):
    total_challans: int
    pending_challans: int
    paid_challans: int
    total_fine_amount: float
    violation_breakdown: Dict[str, int]
    period: str
    last_updated: str

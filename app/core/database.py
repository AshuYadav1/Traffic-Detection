"""
Database configuration and models
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Text, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database URL from environment or default to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./traffic_violations.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Models
class Violation(Base):
    __tablename__ = "violations"
    
    id = Column(Integer, primary_key=True, index=True)
    violation_type = Column(String(50), nullable=False)  # 'red_light', 'helmet', 'wrong_way'
    vehicle_type = Column(String(50))  # 'car', 'motorcycle', 'truck', 'bus'
    tracker_id = Column(Integer)
    confidence = Column(Float)
    frame_number = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)
    location = Column(String(255))  # Optional location info
    jurisdiction = Column(String(100))  # RTO jurisdiction
    
    # Evidence file paths
    evidence_image_path = Column(String(500))
    evidence_video_path = Column(String(500))
    
    # Processing metadata
    processing_time = Column(Float)  # Time taken to process
    video_duration = Column(Float)  # Original video duration
    violation_coordinates = Column(Text)  # JSON string of bounding box coordinates
    
    # Status fields
    is_verified = Column(Boolean, default=False)
    is_processed = Column(Boolean, default=False)
    notes = Column(Text)

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String(100), unique=True, index=True)
    video_path = Column(String(500), nullable=False)
    status = Column(String(50), default="pending")  # 'pending', 'processing', 'completed', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Processing parameters
    traffic_direction = Column(String(20), default="right")
    confidence_threshold = Column(Float, default=0.5)
    min_motorcycle_area = Column(Integer, default=3000)
    
    # Results
    total_violations = Column(Integer, default=0)
    red_light_violations = Column(Integer, default=0)
    helmet_violations = Column(Integer, default=0)
    wrong_way_violations = Column(Integer, default=0)
    
    # Error handling
    error_message = Column(Text)
    
    # Relationships
    violations = relationship("Violation", back_populates="job")

# Add relationship to Violation model
Violation.job_id = Column(Integer, ForeignKey("processing_jobs.id"), nullable=True)
Violation.job = relationship("ProcessingJob", back_populates="violations")

class TrafficPolice(Base):
    __tablename__ = "traffic_police"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    badge_number = Column(String(50), nullable=False)
    profile_image = Column(String(500))
    assigned_area = Column(Text)  # JSON string for area data
    rto_office_id = Column(Integer)
    status = Column(String(20), default="active")  # 'active', 'inactive', 'suspended'
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    e_challans = relationship("EChallan", back_populates="traffic_police")

class EChallan(Base):
    __tablename__ = "e_challans"
    
    id = Column(Integer, primary_key=True, index=True)
    challan_number = Column(String(50), unique=True, index=True)
    traffic_police_id = Column(Integer, ForeignKey("traffic_police.id"), nullable=False)
    violation_id = Column(Integer, ForeignKey("violations.id"))
    vehicle_number = Column(String(20), nullable=False)
    violation_type = Column(String(50), nullable=False)
    fine_amount = Column(Float, nullable=False)
    location = Column(Text)  # JSON string for location data
    description = Column(Text)
    status = Column(String(20), default="pending")  # 'pending', 'paid', 'disputed', 'cancelled'
    created_at = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime)
    
    # Relationships
    traffic_police = relationship("TrafficPolice", back_populates="e_challans")
    violation = relationship("Violation")

class CitizenReport(Base):
    __tablename__ = "citizen_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(50), unique=True, index=True)
    incident_type = Column(String(100), nullable=False)
    priority = Column(String(20), nullable=False)  # 'Low', 'Medium', 'High', 'Critical'
    description = Column(Text, nullable=False)
    vehicle_number = Column(String(20))
    reporter_name = Column(String(255), nullable=False)
    reporter_phone = Column(String(20), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location = Column(String(255), nullable=False)
    attachment_paths = Column(Text)  # JSON string for file paths
    status = Column(String(20), default="submitted")  # 'submitted', 'assigned', 'under_review', 'resolved', 'rejected'
    assigned_to = Column(Integer, ForeignKey("traffic_police.id"))
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    assigned_officer = relationship("TrafficPolice")

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

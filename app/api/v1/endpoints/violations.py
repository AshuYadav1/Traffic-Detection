"""
Violation data endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db, Violation
from app.schemas.violation import ViolationResponse, ViolationStats
from app.core.config import settings
import os
import glob
from typing import Dict, Any

router = APIRouter()

@router.get("/", response_model=List[ViolationResponse])
async def get_violations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    violation_type: Optional[str] = Query(None),
    vehicle_type: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get list of violations with optional filtering
    """
    query = db.query(Violation)
    
    # Apply filters
    if violation_type:
        query = query.filter(Violation.violation_type == violation_type)
    
    if vehicle_type:
        query = query.filter(Violation.vehicle_type == vehicle_type)
    
    if start_date:
        query = query.filter(Violation.timestamp >= start_date)
    
    if end_date:
        query = query.filter(Violation.timestamp <= end_date)
    
    # Order by timestamp (newest first)
    query = query.order_by(Violation.timestamp.desc())
    
    # Apply pagination
    violations = query.offset(skip).limit(limit).all()
    
    return violations

@router.get("/stats", response_model=ViolationStats)
async def get_violation_stats(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get violation statistics for the specified number of days
    """
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get total violations
    total_violations = db.query(Violation).filter(
        Violation.timestamp >= start_date
    ).count()
    
    # Get violations by type
    red_light_violations = db.query(Violation).filter(
        Violation.violation_type == "red_light",
        Violation.timestamp >= start_date
    ).count()
    
    helmet_violations = db.query(Violation).filter(
        Violation.violation_type == "helmet",
        Violation.timestamp >= start_date
    ).count()
    
    wrong_way_violations = db.query(Violation).filter(
        Violation.violation_type == "wrong_way",
        Violation.timestamp >= start_date
    ).count()
    
    # Get violations by vehicle type
    vehicle_stats = db.query(
        Violation.vehicle_type,
        db.func.count(Violation.id)
    ).filter(
        Violation.timestamp >= start_date
    ).group_by(Violation.vehicle_type).all()
    
    vehicle_type_stats = {vehicle_type: count for vehicle_type, count in vehicle_stats}
    
    # Get daily violation counts
    daily_violations = db.query(
        db.func.date(Violation.timestamp).label('date'),
        db.func.count(Violation.id).label('count')
    ).filter(
        Violation.timestamp >= start_date
    ).group_by(db.func.date(Violation.timestamp)).all()
    
    daily_stats = {str(date): count for date, count in daily_violations}
    
    return ViolationStats(
        total_violations=total_violations,
        red_light_violations=red_light_violations,
        helmet_violations=helmet_violations,
        wrong_way_violations=wrong_way_violations,
        vehicle_type_stats=vehicle_type_stats,
        daily_violations=daily_stats,
        period_days=days
    )

@router.get("/{violation_id}", response_model=ViolationResponse)
async def get_violation(violation_id: int, db: Session = Depends(get_db)):
    """
    Get a specific violation by ID
    """
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    return violation

@router.put("/{violation_id}/verify")
async def verify_violation(
    violation_id: int,
    is_verified: bool = True,
    notes: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Mark a violation as verified or not verified
    """
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    violation.is_verified = is_verified
    if notes:
        violation.notes = notes
    
    db.commit()
    
    return {"message": f"Violation {'verified' if is_verified else 'unverified'} successfully"}

@router.delete("/{violation_id}")
async def delete_violation(violation_id: int, db: Session = Depends(get_db)):
    """
    Delete a violation (admin only)
    """
    violation = db.query(Violation).filter(Violation.id == violation_id).first()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")
    
    # Delete evidence files if they exist
    if violation.evidence_image_path and os.path.exists(violation.evidence_image_path):
        os.remove(violation.evidence_image_path)
    
    db.delete(violation)
    db.commit()
    
    return {"message": "Violation deleted successfully"}

@router.get("/evidence/gallery")
async def get_evidence_gallery(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    violation_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get evidence images for the violation gallery
    """
    evidence_dir = settings.EVIDENCE_DIR
    
    if not os.path.exists(evidence_dir):
        return {"images": [], "total": 0}
    
    # Find all evidence images
    image_files = []
    for root, dirs, files in os.walk(evidence_dir):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Extract violation info from filename
                filename = file
                job_id = os.path.basename(root)
                
                # Parse violation type from filename
                violation_type_from_file = "unknown"
                if "red_light" in filename:
                    violation_type_from_file = "red_light"
                elif "helmet" in filename:
                    violation_type_from_file = "helmet"
                elif "wrong_way" in filename:
                    violation_type_from_file = "wrong_way"
                
                # Apply filter if specified
                if violation_type and violation_type_from_file != violation_type:
                    continue
                
                # Extract frame number and vehicle info
                frame_number = "unknown"
                vehicle_type = "unknown"
                
                # Parse frame number
                if "frame" in filename:
                    try:
                        frame_part = filename.split("frame")[1].split(".")[0]
                        frame_number = frame_part
                    except:
                        pass
                
                # Parse vehicle type
                if "motorcycle" in filename:
                    vehicle_type = "motorcycle"
                elif "car" in filename:
                    vehicle_type = "car"
                elif "truck" in filename:
                    vehicle_type = "truck"
                
                image_info = {
                    "filename": filename,
                    "job_id": job_id,
                    "violation_type": violation_type_from_file,
                    "vehicle_type": vehicle_type,
                    "frame_number": frame_number,
                    "image_url": f"/api/v1/videos/evidence/{job_id}/{filename}",
                    "full_path": os.path.join(root, file)
                }
                image_files.append(image_info)
    
    # Sort by filename (newest first)
    image_files.sort(key=lambda x: x['filename'], reverse=True)
    
    # Apply pagination
    total = len(image_files)
    paginated_images = image_files[skip:skip + limit]
    
    return {
        "images": paginated_images,
        "total": total,
        "skip": skip,
        "limit": limit
    }

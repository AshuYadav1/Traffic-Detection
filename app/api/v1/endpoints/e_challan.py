"""
E-Challan Management API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uuid

from app.core.database import get_db, Violation, ProcessingJob
from app.services.vehicle_info_service import vehicle_service
from app.services.challan_pdf_service import challan_pdf_service
from app.services.email_service import send_challan_email

router = APIRouter()

@router.get("/vehicle-info")
async def get_vehicle_info(first: str, second: str):
    """
    Get vehicle information from registration number
    """
    try:
        vehicle_info = await vehicle_service.get_vehicle_info(first, second)
        return vehicle_info
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching vehicle info: {str(e)}")

@router.get("/violations")
async def get_all_violations(
    skip: int = 0,
    limit: int = 100,
    violation_type: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all violations for E-Challan management
    """
    try:
        query = db.query(Violation)
        
        if violation_type:
            query = query.filter(Violation.violation_type == violation_type)
        
        violations = query.offset(skip).limit(limit).all()
        
        # Convert to dict with additional info
        violation_list = []
        for violation in violations:
            violation_dict = {
                "id": violation.id,
                "violation_type": violation.violation_type,
                "vehicle_type": violation.vehicle_type,
                "tracker_id": violation.tracker_id,
                "confidence": violation.confidence,
                "frame_number": violation.frame_number,
                "timestamp": violation.timestamp.isoformat(),
                "location": violation.location,
                "jurisdiction": violation.jurisdiction,
                "evidence_image_path": violation.evidence_image_path,
                "evidence_video_path": violation.evidence_video_path,
                "violation_coordinates": violation.violation_coordinates,
                "is_verified": violation.is_verified,
                "is_processed": violation.is_processed,
                "notes": violation.notes,
                "processing_time": violation.processing_time,
                "video_duration": violation.video_duration,
                # Add license plate info if available
                "license_plate": "1206SHL" if violation.id % 3 == 0 else f"MH{12 + violation.id}DE{1400 + violation.id}",
                "challan_amount": _calculate_challan_amount(violation.violation_type),
                "due_date": (datetime.utcnow() + timedelta(days=15)).isoformat(),
                "status": "Pending"
            }
            violation_list.append(violation_dict)
        
        return {
            "violations": violation_list,
            "total": len(violation_list),
            "skip": skip,
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching violations: {str(e)}")

@router.post("/generate-challan/{violation_id}")
async def generate_challan(
    violation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate and email E-Challan for a violation
    """
    try:
        # Get violation details
        violation = db.query(Violation).filter(Violation.id == violation_id).first()
        if not violation:
            raise HTTPException(status_code=404, detail="Violation not found")
        
        # Get vehicle information from registration database
        license_plate = "1206SHL" if violation.id % 3 == 0 else f"MH{12 + violation.id}DE{1400 + violation.id}"
        first_part = license_plate[:4] if len(license_plate) > 4 else license_plate[:2]
        second_part = license_plate[4:] if len(license_plate) > 4 else license_plate[2:]
        
        vehicle_info = await vehicle_service.get_vehicle_info(first_part, second_part)
        
        # Generate challan data
        challan_data = {
            "challan_id": f"DL{datetime.now().strftime('%Y%m%d')}{violation_id:04d}",
            "violation_id": violation_id,
            "license_plate": license_plate,
            "violation_type": violation.violation_type,
            "vehicle_type": violation.vehicle_type,
            "timestamp": violation.timestamp.strftime("%d-%m-%Y %H:%M:%S"),
            "location": violation.location or "Traffic Signal, Delhi",
            "challan_amount": _calculate_challan_amount(violation.violation_type),
            "due_date": (datetime.utcnow() + timedelta(days=15)).strftime("%d-%m-%Y"),
            "officer_name": "Inspector Rajesh Kumar",
            "officer_id": "DL2023001",
            "court_address": "Metropolitan Magistrate Court, Delhi",
            "vehicle_info": vehicle_info,
            "confidence": violation.confidence,
            "evidence_path": violation.evidence_image_path
        }
        
        # Generate PDF in background
        background_tasks.add_task(
            _generate_and_send_challan,
            challan_data
        )
        
        return {
            "message": "E-Challan generation initiated",
            "challan_id": challan_data["challan_id"],
            "status": "Processing"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating challan: {str(e)}")

@router.get("/challans")
async def get_generated_challans(db: Session = Depends(get_db)):
    """
    Get all generated e-challans
    """
    try:
        # Get recent violations to show as challans
        violations = db.query(Violation).order_by(Violation.timestamp.desc()).limit(20).all()
        
        challans = []
        for violation in violations:
            license_plate = "1206SHL" if violation.id % 3 == 0 else f"MH{12 + violation.id}DE{1400 + violation.id}"
            challan = {
                "challan_id": f"DL{datetime.now().strftime('%Y%m%d')}{violation.id:04d}",
                "violation_id": violation.id,
                "license_plate": license_plate,
                "violation_type": violation.violation_type,
                "amount": _calculate_challan_amount(violation.violation_type),
                "status": "Sent" if violation.id % 2 == 0 else "Pending",
                "generated_date": violation.timestamp.strftime("%d-%m-%Y"),
                "due_date": (violation.timestamp + timedelta(days=15)).strftime("%d-%m-%Y"),
                "owner_name": _get_mock_owner_name(license_plate),
                "vehicle_type": violation.vehicle_type
            }
            challans.append(challan)
        
        return {
            "challans": challans,
            "total": len(challans)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching challans: {str(e)}")

async def _generate_and_send_challan(challan_data: Dict[str, Any]):
    """
    Background task to generate PDF and send email
    """
    try:
        # Generate PDF
        pdf_path = await challan_pdf_service.generate_challan_pdf(challan_data)
        
        # Email list as specified
        email_list = [
            "aashukumaryadav1@gmail.com",
            "aaditya.sawant23@spit.ac.in",
            "jeet.patel23@spit.ac.in",
            "devansh.sarda23@spit.ac.in"
        ]
        
        # Send emails to all recipients
        for email in email_list:
            await send_challan_email(
                to_email=email,
                challan_data=challan_data,
                pdf_path=pdf_path
            )
        
        print(f"✅ E-Challan {challan_data['challan_id']} sent to all recipients")
        
    except Exception as e:
        print(f"❌ Error in challan generation: {e}")

def _calculate_challan_amount(violation_type: str) -> int:
    """
    Calculate challan amount based on violation type
    """
    amounts = {
        "red_light": 1000,
        "helmet": 500,
        "wrong_way": 1500,
        "overspeeding": 2000,
        "no_parking": 200,
        "mobile_phone": 1000
    }
    return amounts.get(violation_type, 500)

def _get_mock_owner_name(license_plate: str) -> str:
    """
    Get mock owner name based on license plate
    """
    if license_plate == "1206SHL":
        return "Rohan Mehra"
    elif "MH" in license_plate:
        return "Ramesh Kumar"
    elif "DL" in license_plate:
        return "Anita Sharma"
    else:
        return "Vehicle Owner"

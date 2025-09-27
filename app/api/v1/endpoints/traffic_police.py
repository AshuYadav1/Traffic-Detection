"""
Traffic Police API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
import hashlib
import secrets
import json

from app.core.database import get_db, TrafficPolice, EChallan, CitizenReport
from app.schemas.traffic_police import (
    TrafficPoliceCreate, 
    TrafficPoliceResponse, 
    TrafficPoliceLogin,
    TrafficPoliceUpdate,
    EChallanCreate,
    EChallanResponse
)
from app.services.email_service import email_service

router = APIRouter()

@router.get("/list", response_model=List[TrafficPoliceResponse])
async def list_traffic_police(db: Session = Depends(get_db)):
    """
    Get list of all traffic police officers
    """
    try:
        officers = db.query(TrafficPolice).all()
        return [
            TrafficPoliceResponse(
                id=officer.id,
                employee_id=officer.employee_id,
                name=officer.name,
                email=officer.email,
                badge_number=officer.badge_number,
                profile_image=officer.profile_image,
                assigned_area=json.loads(officer.assigned_area) if officer.assigned_area else {},
                rto_office_id=officer.rto_office_id,
                status=officer.status,
                created_at=officer.created_at.isoformat()
            )
            for officer in officers
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching traffic police list: {str(e)}"
        )

@router.post("/register", response_model=TrafficPoliceResponse)
async def register_traffic_police(
    police_data: TrafficPoliceCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new traffic police officer
    """
    try:
        # Check if email already exists
        existing_officer = db.query(TrafficPolice).filter(TrafficPolice.email == police_data.email).first()
        if existing_officer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Generate employee ID
        officer_count = db.query(TrafficPolice).count()
        employee_id = f"TP{officer_count + 1:04d}"
        
        # Hash password
        password_hash = hashlib.sha256(police_data.password.encode()).hexdigest()
        
        # Create traffic police record
        police_record = TrafficPolice(
            employee_id=employee_id,
            name=police_data.name,
            email=police_data.email,
            password_hash=password_hash,
            badge_number=police_data.badge_number,
            profile_image=police_data.profile_image,
            assigned_area=json.dumps(police_data.assigned_area),
            rto_office_id=police_data.rto_office_id,
            status="active"
        )
        
        db.add(police_record)
        db.commit()
        db.refresh(police_record)
        
        # Send welcome email
        try:
            assigned_area_name = "Unknown Area"
            if police_data.assigned_area and hasattr(police_data.assigned_area, 'name'):
                assigned_area_name = police_data.assigned_area.name
            elif police_data.assigned_area and isinstance(police_data.assigned_area, dict):
                assigned_area_name = police_data.assigned_area.get('name', 'Unknown Area')
            
            login_credentials = {
                "email": police_data.email,
                "password": police_data.password
            }
            
            await email_service.send_welcome_email(
                to_email=police_data.email,
                officer_name=police_data.name,
                employee_id=employee_id,
                badge_number=police_data.badge_number,
                assigned_area=assigned_area_name,
                login_credentials=login_credentials
            )
            print(f"✅ Welcome email sent to {police_data.email}")
        except Exception as e:
            print(f"⚠️ Failed to send welcome email to {police_data.email}: {str(e)}")
            # Registration continues even if email fails
        
        return TrafficPoliceResponse(
            id=police_record.id,
            employee_id=police_record.employee_id,
            name=police_record.name,
            email=police_record.email,
            badge_number=police_record.badge_number,
            profile_image=police_record.profile_image,
            assigned_area=json.loads(police_record.assigned_area) if police_record.assigned_area else {},
            rto_office_id=police_record.rto_office_id,
            status=police_record.status,
            created_at=police_record.created_at.isoformat()
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error registering traffic police: {str(e)}"
        )

@router.post("/login")
async def login_traffic_police(
    login_data: TrafficPoliceLogin,
    db: Session = Depends(get_db)
):
    """
    Login traffic police officer
    """
    try:
        # Check if email exists
        police_record = db.query(TrafficPolice).filter(TrafficPolice.email == login_data.email).first()
        if not police_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        password_hash = hashlib.sha256(login_data.password.encode()).hexdigest()
        if police_record.password_hash != password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if account is active
        if police_record.status != "active":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Update last login
        police_record.last_login = datetime.utcnow()
        db.commit()
        
        # Generate session token (simplified)
        session_token = secrets.token_urlsafe(32)
        
        return {
            "access_token": session_token,
            "token_type": "bearer",
            "expires_in": 3600,  # 1 hour
            "police_data": TrafficPoliceResponse(
                id=police_record.id,
                employee_id=police_record.employee_id,
                name=police_record.name,
                email=police_record.email,
                badge_number=police_record.badge_number,
                profile_image=police_record.profile_image,
                assigned_area=json.loads(police_record.assigned_area) if police_record.assigned_area else {},
                rto_office_id=police_record.rto_office_id,
                status=police_record.status,
                created_at=police_record.created_at.isoformat()
            )
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during login: {str(e)}"
        )

@router.get("/profile/{police_id}", response_model=TrafficPoliceResponse)
async def get_police_profile(
    police_id: int,
    db: Session = Depends(get_db)
):
    """
    Get traffic police profile
    """
    try:
        # Find police record
        police_record = None
        for email, record in traffic_police_db.items():
            if record["id"] == police_id:
                police_record = record
                break
        
        if not police_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Traffic police not found"
            )
        
        return TrafficPoliceResponse(
            id=police_record["id"],
            employee_id=police_record["employee_id"],
            name=police_record["name"],
            email=police_record["email"],
            badge_number=police_record["badge_number"],
            profile_image=police_record["profile_image"],
            assigned_area=police_record["assigned_area"],
            rto_office_id=police_record["rto_office_id"],
            status=police_record["status"],
            created_at=police_record["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching profile: {str(e)}"
        )

@router.get("/alerts/{police_id}")
async def get_live_violation_alerts(
    police_id: int,
    db: Session = Depends(get_db)
):
    """
    Get live violation alerts for assigned area
    """
    try:
        # Find police record
        police_record = db.query(TrafficPolice).filter(TrafficPolice.id == police_id).first()
        
        if not police_record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Traffic police not found"
            )
        
        # Get assigned area
        assigned_area = json.loads(police_record.assigned_area) if police_record.assigned_area else {}
        area_name = assigned_area.get("name", "Unknown Area")
        
        # Get real citizen reports assigned to this police officer
        citizen_reports = db.query(CitizenReport).filter(
            CitizenReport.assigned_to == police_id,
            CitizenReport.status.in_(["submitted", "approved"])
        ).order_by(CitizenReport.created_at.desc()).limit(20).all()
        
        # Convert citizen reports to alerts format
        alerts = []
        for report in citizen_reports:
            alert = {
                "id": report.report_id,
                "violation_type": report.incident_type.lower().replace(" ", "_"),
                "vehicle_number": report.vehicle_number or "Unknown",
                "location": {
                    "latitude": report.latitude,
                    "longitude": report.longitude,
                    "address": report.location or f"{area_name} - {report.latitude}, {report.longitude}"
                },
                "timestamp": report.created_at.isoformat(),
                "confidence": 0.95,  # High confidence for citizen reports
                "evidence_image": f"/uploads/citizen_reports/{report.report_id}/" if report.attachment_paths else None,
                "status": "pending" if report.status == "submitted" else "approved",
                "assigned_area": area_name,
                "description": report.description,
                "reporter_name": report.reporter_name,
                "reporter_phone": report.reporter_phone,
                "attachment_paths": json.loads(report.attachment_paths) if report.attachment_paths else [],
                "citizen_report_id": report.report_id
            }
            alerts.append(alert)
        
        return {
            "alerts": alerts,
            "total_alerts": len(alerts),
            "assigned_area": area_name,
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching alerts: {str(e)}"
        )

@router.post("/challan", response_model=EChallanResponse)
async def create_e_challan(
    challan_data: EChallanCreate,
    db: Session = Depends(get_db)
):
    """
    Create e-challan
    """
    try:
        # Generate challan number
        challan_number = f"CH{datetime.utcnow().strftime('%Y%m%d')}{len(e_challans_db) + 1:04d}"
        
        # Create challan record
        challan_record = {
            "id": len(e_challans_db) + 1,
            "challan_number": challan_number,
            "traffic_police_id": challan_data.traffic_police_id,
            "violation_id": challan_data.violation_id,
            "vehicle_number": challan_data.vehicle_number,
            "violation_type": challan_data.violation_type,
            "fine_amount": challan_data.fine_amount,
            "location": challan_data.location,
            "description": challan_data.description,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "due_date": (datetime.utcnow() + timedelta(days=30)).isoformat()
        }
        
        e_challans_db[challan_number] = challan_record
        
        return EChallanResponse(
            id=challan_record["id"],
            challan_number=challan_record["challan_number"],
            traffic_police_id=challan_record["traffic_police_id"],
            violation_id=challan_record["violation_id"],
            vehicle_number=challan_record["vehicle_number"],
            violation_type=challan_record["violation_type"],
            fine_amount=challan_record["fine_amount"],
            location=challan_record["location"],
            description=challan_record["description"],
            status=challan_record["status"],
            created_at=challan_record["created_at"],
            due_date=challan_record["due_date"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating e-challan: {str(e)}"
        )

@router.get("/challans/{police_id}")
async def get_police_challans(
    police_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get e-challans created by traffic police
    """
    try:
        # Filter challans by police ID
        police_challans = db.query(EChallan).filter(EChallan.traffic_police_id == police_id).offset(skip).limit(limit).all()
        total = db.query(EChallan).filter(EChallan.traffic_police_id == police_id).count()
        
        # Convert to response format
        challans_data = []
        for challan in police_challans:
            challans_data.append({
                "id": challan.id,
                "challan_number": challan.challan_number,
                "traffic_police_id": challan.traffic_police_id,
                "violation_id": challan.violation_id,
                "vehicle_number": challan.vehicle_number,
                "violation_type": challan.violation_type,
                "fine_amount": challan.fine_amount,
                "location": json.loads(challan.location) if challan.location else {},
                "description": challan.description,
                "status": challan.status,
                "created_at": challan.created_at.isoformat(),
                "due_date": challan.due_date.isoformat() if challan.due_date else None
            })
        
        return {
            "challans": challans_data,
            "total": total,
            "skip": skip,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching challans: {str(e)}"
        )

@router.get("/stats/{police_id}")
async def get_police_stats(
    police_id: int,
    db: Session = Depends(get_db)
):
    """
    Get traffic police statistics
    """
    try:
        # Get challans created by this police
        police_challans = db.query(EChallan).filter(EChallan.traffic_police_id == police_id).all()
        
        # Get citizen reports assigned to this police
        citizen_reports = db.query(CitizenReport).filter(CitizenReport.assigned_to == police_id).all()
        
        # Calculate statistics
        total_challans = len(police_challans)
        pending_challans = len([c for c in police_challans if c.status == "pending"])
        paid_challans = len([c for c in police_challans if c.status == "paid"])
        total_fine_amount = sum([c.fine_amount for c in police_challans])
        
        # Citizen report statistics
        total_citizen_reports = len(citizen_reports)
        pending_reports = len([r for r in citizen_reports if r.status == "submitted"])
        approved_reports = len([r for r in citizen_reports if r.status == "approved"])
        rejected_reports = len([r for r in citizen_reports if r.status == "rejected"])
        
        # Get violation type breakdown from both challans and citizen reports
        violation_types = {}
        for challan in police_challans:
            vtype = challan.violation_type
            violation_types[vtype] = violation_types.get(vtype, 0) + 1
        
        for report in citizen_reports:
            vtype = report.incident_type
            violation_types[vtype] = violation_types.get(vtype, 0) + 1
        
        return {
            "total_challans": total_challans,
            "pending_challans": pending_challans,
            "paid_challans": paid_challans,
            "total_fine_amount": total_fine_amount,
            "total_citizen_reports": total_citizen_reports,
            "pending_reports": pending_reports,
            "approved_reports": approved_reports,
            "rejected_reports": rejected_reports,
            "violation_breakdown": violation_types,
            "period": "last_30_days",
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )

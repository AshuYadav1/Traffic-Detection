"""
Citizen Reports API endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import json
from datetime import datetime

from app.core.database import get_db, CitizenReport, TrafficPolice
from app.core.config import settings
from app.schemas.citizen_report import CitizenReportCreate, CitizenReportResponse
from app.services.notification_service import notification_service

router = APIRouter()

@router.post("/", response_model=CitizenReportResponse)
async def create_citizen_report(
    background_tasks: BackgroundTasks,
    incident_type: str = Form(...),
    priority: str = Form(...),
    description: str = Form(...),
    reporter_name: str = Form(...),
    reporter_phone: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    location: str = Form(...),
    vehicle_number: Optional[str] = Form(None),
    attachments: List[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    """
    Create a new citizen report
    """
    try:
        # Generate unique report ID
        report_id = str(uuid.uuid4())
        
        # Create upload directory for this report
        report_upload_dir = os.path.join(settings.UPLOAD_DIR, "citizen_reports", report_id)
        os.makedirs(report_upload_dir, exist_ok=True)
        
        # Save uploaded files
        attachment_paths = []
        if attachments:
            for attachment in attachments:
                if attachment.filename:
                    file_path = os.path.join(report_upload_dir, attachment.filename)
                    with open(file_path, "wb") as buffer:
                        content = await attachment.read()
                        buffer.write(content)
                    attachment_paths.append(file_path)
        
        # Find nearest traffic police officer
        assigned_officer = _find_nearest_officer(latitude, longitude, db)
        
        # Create citizen report record
        report = CitizenReport(
            report_id=report_id,
            incident_type=incident_type,
            priority=priority,
            description=description,
            vehicle_number=vehicle_number,
            reporter_name=reporter_name,
            reporter_phone=reporter_phone,
            latitude=latitude,
            longitude=longitude,
            location=location,
            attachment_paths=json.dumps(attachment_paths) if attachment_paths else None,
            status="submitted",
            assigned_to=assigned_officer.id if assigned_officer else None
        )
        
        db.add(report)
        db.commit()
        db.refresh(report)
        
        # Send notifications in background
        if assigned_officer:
            background_tasks.add_task(
                _send_notifications,
                report_id,
                assigned_officer.id,
                incident_type,
                priority
            )
        
        return CitizenReportResponse(
            report_id=report_id,
            incident_type=incident_type,
            priority=priority,
            description=description,
            status="submitted",
            created_at=report.created_at.isoformat(),
            assigned_officer=assigned_officer.name if assigned_officer else None,
            message="Report submitted successfully",
            attachment_paths=attachment_paths,
            reporter_name=reporter_name,
            reporter_phone=reporter_phone,
            location=location,
            vehicle_number=vehicle_number
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error creating report: {str(e)}"
        )

@router.get("/", response_model=List[CitizenReportResponse])
async def get_citizen_reports(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    incident_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all citizen reports with filtering
    """
    query = db.query(CitizenReport)
    
    if status:
        query = query.filter(CitizenReport.status == status)
    if incident_type:
        query = query.filter(CitizenReport.incident_type == incident_type)
    
    reports = query.offset(skip).limit(limit).all()
    
    return [
        CitizenReportResponse(
            report_id=report.report_id,
            incident_type=report.incident_type,
            priority=report.priority,
            description=report.description,
            status=report.status,
            created_at=report.created_at.isoformat(),
            assigned_officer=report.assigned_officer.name if report.assigned_officer else None,
            attachment_paths=json.loads(report.attachment_paths) if report.attachment_paths else None,
            reporter_name=report.reporter_name,
            reporter_phone=report.reporter_phone,
            location=report.location,
            vehicle_number=report.vehicle_number
        )
        for report in reports
    ]

@router.get("/{report_id}", response_model=CitizenReportResponse)
async def get_citizen_report(report_id: str, db: Session = Depends(get_db)):
    """
    Get a specific citizen report
    """
    report = db.query(CitizenReport).filter(CitizenReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    return CitizenReportResponse(
        report_id=report.report_id,
        incident_type=report.incident_type,
        priority=report.priority,
        description=report.description,
        status=report.status,
        created_at=report.created_at.isoformat(),
        assigned_officer=report.assigned_officer.name if report.assigned_officer else None,
        attachment_paths=json.loads(report.attachment_paths) if report.attachment_paths else None,
        reporter_name=report.reporter_name,
        reporter_phone=report.reporter_phone,
        location=report.location,
        vehicle_number=report.vehicle_number
    )

@router.put("/{report_id}/assign")
async def assign_report(
    report_id: str,
    officer_id: int,
    db: Session = Depends(get_db)
):
    """
    Assign a report to a traffic police officer
    """
    report = db.query(CitizenReport).filter(CitizenReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    officer = db.query(TrafficPolice).filter(TrafficPolice.id == officer_id).first()
    if not officer:
        raise HTTPException(status_code=404, detail="Officer not found")
    
    report.assigned_to = officer_id
    report.status = "assigned"
    db.commit()
    
    # Send notification to officer
    await notification_service.send_notification(
        officer_id=officer_id,
        title="New Report Assigned",
        message=f"Report {report_id} has been assigned to you",
        type="report_assignment"
    )
    
    return {"message": "Report assigned successfully"}

@router.put("/{report_id}/status")
async def update_report_status(
    report_id: str,
    status: str,
    feedback: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Update report status
    """
    report = db.query(CitizenReport).filter(CitizenReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.status = status
    if feedback:
        report.feedback = feedback
    db.commit()
    
    return {"message": "Report status updated successfully"}

@router.put("/{report_id}/approve")
async def approve_report(
    report_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Approve a citizen report and notify traffic police
    """
    report = db.query(CitizenReport).filter(CitizenReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Update report status
    report.status = "approved"
    db.commit()
    
    # Send notification to assigned officer
    if report.assigned_to:
        background_tasks.add_task(
            _send_approval_notification,
            report_id,
            report.assigned_to,
            report.incident_type,
            report.location
        )
    
    return {"message": "Report approved successfully"}

@router.put("/{report_id}/reject")
async def reject_report(
    report_id: str,
    feedback: str,
    db: Session = Depends(get_db)
):
    """
    Reject a citizen report
    """
    report = db.query(CitizenReport).filter(CitizenReport.report_id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    report.status = "rejected"
    report.feedback = feedback
    db.commit()
    
    return {"message": "Report rejected successfully"}

def _find_nearest_officer(latitude: float, longitude: float, db: Session) -> Optional[TrafficPolice]:
    """
    Find the nearest traffic police officer based on location using geospatial distance calculation
    """
    from geopy.distance import geodesic
    import json
    
    officers = db.query(TrafficPolice).filter(TrafficPolice.status == "active").all()
    
    if not officers:
        return None
    
    incident_location = (latitude, longitude)
    nearest_officer = None
    min_distance = float('inf')
    
    print(f"🔍 Finding nearest officer for incident at: {latitude}, {longitude}")
    
    for officer in officers:
        if officer.assigned_area:
            try:
                area_data = json.loads(officer.assigned_area)
                if 'coordinates' in area_data:
                    officer_coords = (
                        area_data['coordinates']['lat'],
                        area_data['coordinates']['lng']
                    )
                    
                    # Calculate distance using geodesic distance (most accurate for Earth)
                    distance = geodesic(incident_location, officer_coords).kilometers
                    
                    print(f"👮 Officer {officer.name} ({officer.employee_id}) at {area_data.get('name', 'Unknown')}: {distance:.2f} km")
                    
                    if distance < min_distance:
                        min_distance = distance
                        nearest_officer = officer
                        
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                print(f"⚠️ Error parsing officer {officer.name} area data: {e}")
                continue
    
    if nearest_officer:
        area_data = json.loads(nearest_officer.assigned_area)
        print(f"✅ Assigned to: {nearest_officer.name} ({nearest_officer.employee_id}) at {area_data.get('name', 'Unknown')} - {min_distance:.2f} km away")
    else:
        print("❌ No suitable officer found")
    
    return nearest_officer

async def _send_notifications(report_id: str, officer_id: int, incident_type: str, priority: str):
    """
    Send notifications for new report
    """
    try:
        # Send notification to assigned officer
        await notification_service.send_notification(
            officer_id=officer_id,
            title="New Report Assigned",
            message=f"New {incident_type} report (Priority: {priority})",
            type="report_assignment"
        )
        
        # Send notification to admin dashboard
        await notification_service.send_admin_notification(
            title="New Citizen Report",
            message=f"Report {report_id} submitted and assigned",
            type="citizen_report"
        )
        
    except Exception as e:
        print(f"Error sending notifications: {e}")

async def _send_approval_notification(report_id: str, officer_id: int, incident_type: str, location: str):
    """
    Send notification when report is approved
    """
    try:
        # Send notification to assigned officer with bell sound
        await notification_service.send_notification(
            officer_id=officer_id,
            title="Report Approved",
            message=f"Report {report_id} for {incident_type} at {location} has been approved",
            type="report_approved",
            play_sound=True,
            sound_type="bell"
        )
        
        # Send notification to admin dashboard
        await notification_service.send_admin_notification(
            title="Report Approved",
            message=f"Report {report_id} has been approved and officer notified",
            type="report_approved"
        )
        
    except Exception as e:
        print(f"Error sending approval notifications: {e}")

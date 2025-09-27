"""
Job management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db, ProcessingJob
from app.schemas.job import JobResponse, JobListResponse
import os
import shutil
from app.core.config import settings

router = APIRouter()

@router.get("/", response_model=JobListResponse)
async def get_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get list of processing jobs
    """
    query = db.query(ProcessingJob)
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    # Order by creation time (newest first)
    query = query.order_by(ProcessingJob.created_at.desc())
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    jobs = query.offset(skip).limit(limit).all()
    
    return JobListResponse(
        jobs=jobs,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: Session = Depends(get_db)):
    """
    Get a specific job by ID
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@router.delete("/{job_id}")
async def delete_job(job_id: str, db: Session = Depends(get_db)):
    """
    Delete a job and its associated data
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete associated violations
    from app.core.database import Violation
    violations = db.query(Violation).filter(Violation.job_id == job.id).all()
    for violation in violations:
        # Delete evidence files
        if violation.evidence_image_path and os.path.exists(violation.evidence_image_path):
            os.remove(violation.evidence_image_path)
        db.delete(violation)
    
    # Delete job files
    job_dir = os.path.dirname(job.video_path)
    if os.path.exists(job_dir):
        shutil.rmtree(job_dir)
    
    # Delete evidence directory
    evidence_dir = os.path.join(settings.EVIDENCE_DIR, job_id)
    if os.path.exists(evidence_dir):
        shutil.rmtree(evidence_dir)
    
    # Delete job record
    db.delete(job)
    db.commit()
    
    return {"message": "Job deleted successfully"}

@router.get("/{job_id}/violations")
async def get_job_violations(job_id: str, db: Session = Depends(get_db)):
    """
    Get violations for a specific job
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    from app.core.database import Violation
    violations = db.query(Violation).filter(Violation.job_id == job_id).all()
    
    return violations

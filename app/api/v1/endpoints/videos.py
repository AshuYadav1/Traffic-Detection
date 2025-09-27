"""
Video upload and processing endpoints
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import shutil
from datetime import datetime

from app.core.database import get_db, ProcessingJob
from app.core.config import settings
from app.services.violation_processor import violation_processor
from app.services.simplified_enhanced_processor import SimplifiedEnhancedProcessor
from app.schemas.video import VideoUploadResponse, VideoProcessingRequest
from app.schemas.job import JobResponse
import json

router = APIRouter()

# Initialize enhanced processor
enhanced_processor = SimplifiedEnhancedProcessor()

@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    traffic_direction: str = "right",
    confidence_threshold: float = 0.5,
    min_motorcycle_area: int = 3000,
    db: Session = Depends(get_db)
):
    """
    Upload a video file for violation detection processing
    """
    # Validate file type
    if file.content_type not in settings.ALLOWED_VIDEO_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {settings.ALLOWED_VIDEO_TYPES}"
        )
    
    # Check file size
    file_size = 0
    content = await file.read()
    file_size = len(content)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB"
        )
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    # Create upload directory for this job
    job_upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(job_upload_dir, exist_ok=True)
    
    # Save uploaded file
    file_extension = os.path.splitext(file.filename)[1]
    input_filename = f"input{file_extension}"
    input_path = os.path.join(job_upload_dir, input_filename)
    
    with open(input_path, "wb") as buffer:
        buffer.write(content)
    
    # Create output path
    output_path = os.path.join(job_upload_dir, "output.mp4")
    
    # Create processing job record
    job = ProcessingJob(
        job_id=job_id,
        video_path=input_path,
        status="pending",
        traffic_direction=traffic_direction,
        confidence_threshold=confidence_threshold,
        min_motorcycle_area=min_motorcycle_area
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    # Start background processing
    background_tasks.add_task(
        process_video_background,
        job_id,
        input_path,
        output_path,
        traffic_direction,
        confidence_threshold,
        min_motorcycle_area
    )
    
    return VideoUploadResponse(
        job_id=job_id,
        status="pending",
        message="Video uploaded successfully. Processing started.",
        input_filename=file.filename,
        file_size=file_size
    )

@router.get("/download/{job_id}")
async def download_processed_video(job_id: str, db: Session = Depends(get_db)):
    """
    Download the processed video with violation annotations
    """
    job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Video processing not completed yet")
    
    output_path = os.path.join(os.path.dirname(job.video_path), "output.mp4")
    if not os.path.exists(output_path):
        raise HTTPException(status_code=404, detail="Processed video not found")
    
    return FileResponse(
        path=output_path,
        media_type="video/mp4",
        filename=f"processed_{job_id}.mp4"
    )

@router.get("/evidence/{job_id}/{filename}")
async def get_evidence_image(job_id: str, filename: str):
    """
    Get evidence image for a specific violation
    """
    evidence_path = os.path.join(settings.EVIDENCE_DIR, job_id, filename)
    if not os.path.exists(evidence_path):
        raise HTTPException(status_code=404, detail="Evidence image not found")
    
    return FileResponse(evidence_path)

async def process_video_background(
    job_id: str,
    input_path: str,
    output_path: str,
    traffic_direction: str,
    confidence_threshold: float,
    min_motorcycle_area: int
):
    """
    Background task to process video with WebSocket notifications
    """
    from app.websocket.connection_manager import manager
    
    try:
        # Update job status to processing
        db = next(get_db())
        job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        if job:
            job.status = "processing"
            job.started_at = datetime.utcnow()
            db.commit()
        
        # Add job to active jobs for monitoring
        manager.add_active_job(job_id)
        
        # Send initial progress update
        await manager.send_job_progress(job_id, {
            "status": "processing",
            "frame_count": 0,
            "total_frames": 0,
            "message": "Starting video processing..."
        })
        
        # Process video with enhanced processor
        result = await enhanced_processor.process_video_enhanced(
            input_path=input_path,
            output_path=output_path,
            expected_traffic_direction=traffic_direction,
            min_motorcycle_area=min_motorcycle_area,
            helmet_check_confidence=confidence_threshold,
            job_id=job_id  # Pass job_id for WebSocket notifications
        )
        
        print(f"✅ Video processing completed for job {job_id}: {result}")
        
        # Update job with results
        if job:
            job.status = "completed"
            job.completed_at = datetime.utcnow()
            job.result = json.dumps(result)
            
            # Extract stats from result (they're nested under 'stats' key)
            stats = result.get('stats', {})
            job.red_light_violations = stats.get('red_light_violations', 0)
            job.helmet_violations = stats.get('helmet_violations', 0)
            job.wrong_way_violations = stats.get('wrong_way_violations', 0)
            job.total_violations = job.red_light_violations + job.helmet_violations + job.wrong_way_violations
            db.commit()
        
        # Send completion notification
        await manager.send_job_completed(job_id, result)
        
        # Remove from active jobs
        manager.remove_active_job(job_id)
        
    except Exception as e:
        print(f"❌ Error processing video for job {job_id}: {e}")
        # Update job status to failed
        db = next(get_db())
        job = db.query(ProcessingJob).filter(ProcessingJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
        
        # Send error notification
        await manager.broadcast_to_job(job_id, json.dumps({
            "type": "job_failed",
            "job_id": job_id,
            "error": str(e)
        }))
        
        # Remove from active jobs
        manager.remove_active_job(job_id)
    finally:
        db.close()

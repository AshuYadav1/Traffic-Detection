"""
API v1 router configuration
"""

from fastapi import APIRouter
from app.api.v1.endpoints import videos, violations, jobs, websocket, analytics, audit_simple_real, traffic_police, citizen_reports, e_challan

api_router = APIRouter()

api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(violations.router, prefix="/violations", tags=["violations"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(audit_simple_real.router, prefix="/audit", tags=["audit"])
api_router.include_router(traffic_police.router, prefix="/traffic-police", tags=["traffic-police"])
api_router.include_router(citizen_reports.router, prefix="/citizen-reports", tags=["citizen-reports"])
api_router.include_router(e_challan.router, prefix="/e-challan", tags=["e-challan"])

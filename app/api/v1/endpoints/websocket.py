"""
WebSocket endpoints for real-time communication
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

from app.websocket.connection_manager import ConnectionManager

# Create connection manager instance
connection_manager = ConnectionManager()

router = APIRouter()

@router.websocket("/live")
async def websocket_live_processing(websocket: WebSocket):
    """
    WebSocket endpoint for live video processing updates
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "subscribe_job":
                job_id = message.get("job_id")
                if job_id:
                    await connection_manager.subscribe_to_job(websocket, job_id)
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket error: {e}")
        connection_manager.disconnect(websocket)

@router.websocket("/monitoring")
async def websocket_monitoring(websocket: WebSocket):
    """
    WebSocket endpoint for real-time monitoring dashboard
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Send periodic updates about system status
            await websocket.send_text(json.dumps({
                "type": "status_update",
                "active_connections": len(connection_manager.active_connections),
                "active_jobs": len(connection_manager.active_jobs)
            }))
            
            # Wait before next update
            import asyncio
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket monitoring error: {e}")
        connection_manager.disconnect(websocket)

@router.websocket("/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications to traffic police
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "subscribe_officer":
                officer_id = message.get("officer_id")
                if officer_id:
                    # Subscribe to officer-specific notifications
                    await connection_manager.subscribe_officer(websocket, officer_id)
            
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
    except Exception as e:
        print(f"WebSocket notifications error: {e}")
        connection_manager.disconnect(websocket)

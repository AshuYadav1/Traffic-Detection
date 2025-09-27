"""
WebSocket connection manager for real-time communication
"""

from fastapi import WebSocket
from typing import List, Dict, Set
import json
import asyncio
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.job_subscriptions: Dict[str, Set[WebSocket]] = defaultdict(set)
        self.officer_connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.active_jobs: Set[str] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"✅ WebSocket connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        # Remove from all job subscriptions
        for job_id, subscribers in self.job_subscriptions.items():
            subscribers.discard(websocket)
        
        # Remove from officer connections
        for officer_id, connections in self.officer_connections.items():
            connections.discard(websocket)
        
        print(f"❌ WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def subscribe_to_job(self, websocket: WebSocket, job_id: str):
        """Subscribe a WebSocket to job updates"""
        self.job_subscriptions[job_id].add(websocket)
        print(f"📡 WebSocket subscribed to job {job_id}")
    
    async def unsubscribe_from_job(self, websocket: WebSocket, job_id: str):
        """Unsubscribe a WebSocket from job updates"""
        self.job_subscriptions[job_id].discard(websocket)
        print(f"📡 WebSocket unsubscribed from job {job_id}")
    
    async def subscribe_officer(self, websocket: WebSocket, officer_id: int):
        """Subscribe a WebSocket to officer-specific notifications"""
        self.officer_connections[officer_id].add(websocket)
        websocket.officer_id = officer_id
        print(f"👮 Officer {officer_id} subscribed to notifications")
    
    async def send_to_officer(self, officer_id: int, message: str):
        """Send a message to all connections of a specific officer"""
        if officer_id not in self.officer_connections:
            print(f"⚠️ No connections found for officer {officer_id}")
            return
        
        disconnected = []
        for connection in self.officer_connections[officer_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"❌ Error sending message to officer {officer_id}: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send a message to a specific WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"❌ Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Broadcast a message to all active connections"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"❌ Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
    
    async def broadcast_to_job(self, job_id: str, message: str):
        """Broadcast a message to all subscribers of a specific job"""
        if job_id not in self.job_subscriptions:
            return
        
        disconnected = []
        for connection in self.job_subscriptions[job_id]:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"❌ Error broadcasting to job {job_id} subscriber: {e}")
                disconnected.append(connection)
        
        # Remove disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
            self.job_subscriptions[job_id].discard(connection)
    
    async def send_job_progress(self, job_id: str, progress: Dict):
        """Send job progress update to subscribers"""
        message = json.dumps({
            "type": "job_progress",
            "job_id": job_id,
            "progress": progress
        })
        await self.broadcast_to_job(job_id, message)
    
    async def send_job_completed(self, job_id: str, result: Dict):
        """Send job completion notification to subscribers"""
        message = json.dumps({
            "type": "job_completed",
            "job_id": job_id,
            "result": result
        })
        await self.broadcast_to_job(job_id, message)
    
    async def send_violation_detected(self, job_id: str, violation: Dict):
        """Send violation detection notification to subscribers"""
        message = json.dumps({
            "type": "violation_detected",
            "job_id": job_id,
            "violation": violation
        })
        await self.broadcast_to_job(job_id, message)
    
    def add_active_job(self, job_id: str):
        """Add a job to the active jobs set"""
        self.active_jobs.add(job_id)
    
    def remove_active_job(self, job_id: str):
        """Remove a job from the active jobs set"""
        self.active_jobs.discard(job_id)

# Global connection manager instance
manager = ConnectionManager()

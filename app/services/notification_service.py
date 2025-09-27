"""
Notification service for sending alerts and notifications
"""

import asyncio
import json
from typing import Optional
from app.core.database import get_db, TrafficPolice
from app.websocket.connection_manager import manager

class NotificationService:
    def __init__(self):
        self.manager = manager
    
    async def send_notification(
        self,
        officer_id: int,
        title: str,
        message: str,
        type: str = "general",
        play_sound: bool = False,
        sound_type: str = "bell"
    ):
        """
        Send notification to a specific traffic police officer
        """
        try:
            # Send WebSocket notification to specific officer
            notification_data = json.dumps({
                "type": "notification",
                "title": title,
                "message": message,
                "notification_type": type,
                "officer_id": officer_id,
                "play_sound": play_sound,
                "sound_type": sound_type,
                "timestamp": asyncio.get_event_loop().time()
            })
            
            # Send to specific officer if connected
            await self.manager.send_to_officer(officer_id, notification_data)
            
            # Also broadcast to all connections for admin dashboard
            await self.manager.broadcast(notification_data)
            
            print(f"Notification sent to officer {officer_id}: {title} (Sound: {play_sound})")
            
        except Exception as e:
            print(f"Error sending notification to officer {officer_id}: {e}")
    
    async def send_admin_notification(
        self,
        title: str,
        message: str,
        type: str = "general"
    ):
        """
        Send notification to admin dashboard
        """
        try:
            # Send WebSocket notification to all admin connections
            admin_notification_data = json.dumps({
                "type": "admin_notification",
                "title": title,
                "message": message,
                "notification_type": type,
                "timestamp": asyncio.get_event_loop().time()
            })
            await self.manager.broadcast(admin_notification_data)
            
            print(f"Admin notification sent: {title}")
            
        except Exception as e:
            print(f"Error sending admin notification: {e}")
    
    async def send_citizen_report_alert(
        self,
        report_id: str,
        incident_type: str,
        priority: str,
        location: str,
        assigned_officer_id: Optional[int] = None
    ):
        """
        Send alert for new citizen report
        """
        try:
            # Send to admin dashboard
            await self.send_admin_notification(
                title="New Citizen Report",
                message=f"New {incident_type} report (Priority: {priority}) at {location}",
                type="citizen_report"
            )
            
            # Send to assigned officer if available
            if assigned_officer_id:
                await self.send_notification(
                    officer_id=assigned_officer_id,
                    title="New Report Assigned",
                    message=f"Report {report_id} has been assigned to you",
                    type="report_assignment"
                )
            
        except Exception as e:
            print(f"Error sending citizen report alert: {e}")
    
    async def send_violation_alert(
        self,
        violation_type: str,
        location: str,
        vehicle_number: str,
        assigned_officer_id: Optional[int] = None
    ):
        """
        Send alert for new traffic violation
        """
        try:
            # Send to admin dashboard
            await self.send_admin_notification(
                title="Traffic Violation Detected",
                message=f"{violation_type} by vehicle {vehicle_number} at {location}",
                type="violation_detected"
            )
            
            # Send to assigned officer if available
            if assigned_officer_id:
                await self.send_notification(
                    officer_id=assigned_officer_id,
                    title="Traffic Violation Alert",
                    message=f"{violation_type} detected at {location}",
                    type="violation_alert"
                )
            
        except Exception as e:
            print(f"Error sending violation alert: {e}")

# Global notification service instance
notification_service = NotificationService()

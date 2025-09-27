#!/usr/bin/env python3
"""
Setup demo traffic police users for testing
"""

import sys
import os
import hashlib
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import SessionLocal, TrafficPolice, Base, engine

def create_demo_users():
    """Create demo traffic police users"""
    print("🚀 Setting up demo traffic police users...")
    
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if demo users already exist
        existing_users = db.query(TrafficPolice).count()
        if existing_users > 0:
            print(f"✅ {existing_users} traffic police users already exist in database")
            return
        
        # Demo users data
        demo_users = [
            {
                "employee_id": "TP0001",
                "name": "Officer John Smith",
                "email": "officer1@traffic.gov.in",
                "password": "password123",
                "badge_number": "TP001",
                "profile_image": None,
                "assigned_area": {
                    "name": "Mumbai Central",
                    "coordinates": {"lat": 19.0760, "lng": 72.8777},
                    "jurisdiction": "Mumbai RTO"
                },
                "rto_office_id": 1,
                "status": "active"
            },
            {
                "employee_id": "TP0002",
                "name": "Officer Sarah Johnson",
                "email": "officer2@traffic.gov.in",
                "password": "password123",
                "badge_number": "TP002",
                "profile_image": None,
                "assigned_area": {
                    "name": "Delhi Central",
                    "coordinates": {"lat": 28.6139, "lng": 77.2090},
                    "jurisdiction": "Delhi RTO"
                },
                "rto_office_id": 2,
                "status": "active"
            },
            {
                "employee_id": "TP0003",
                "name": "Officer Rajesh Kumar",
                "email": "officer3@traffic.gov.in",
                "password": "password123",
                "badge_number": "TP003",
                "profile_image": None,
                "assigned_area": {
                    "name": "Bangalore Central",
                    "coordinates": {"lat": 12.9716, "lng": 77.5946},
                    "jurisdiction": "Bangalore RTO"
                },
                "rto_office_id": 3,
                "status": "active"
            }
        ]
        
        # Create users
        for user_data in demo_users:
            # Hash password
            password_hash = hashlib.sha256(user_data["password"].encode()).hexdigest()
            
            # Create traffic police record
            police_record = TrafficPolice(
                employee_id=user_data["employee_id"],
                name=user_data["name"],
                email=user_data["email"],
                password_hash=password_hash,
                badge_number=user_data["badge_number"],
                profile_image=user_data["profile_image"],
                assigned_area=json.dumps(user_data["assigned_area"]),
                rto_office_id=user_data["rto_office_id"],
                status=user_data["status"]
            )
            
            db.add(police_record)
            print(f"✅ Created user: {user_data['name']} ({user_data['email']})")
        
        # Commit all changes
        db.commit()
        print(f"🎉 Successfully created {len(demo_users)} demo traffic police users!")
        
        # Display login credentials
        print("\n📋 Demo Login Credentials:")
        print("=" * 50)
        for user_data in demo_users:
            print(f"Email: {user_data['email']}")
            print(f"Password: {user_data['password']}")
            print(f"Name: {user_data['name']}")
            print(f"Badge: {user_data['badge_number']}")
            print("-" * 30)
        
    except Exception as e:
        print(f"❌ Error creating demo users: {e}")
        db.rollback()
        return False
    finally:
        db.close()
    
    return True

def main():
    """Main function"""
    print("🚀 Traffic Police Demo Users Setup")
    print("=" * 50)
    
    if create_demo_users():
        print("\n✅ Demo users setup completed successfully!")
        print("\n🚀 You can now test the login functionality with the demo credentials above.")
    else:
        print("\n❌ Demo users setup failed!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

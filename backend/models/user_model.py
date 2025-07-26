"""
User model for user management and authentication
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
import structlog

from backend.models.base_model import BaseModel

logger = structlog.get_logger()


class User(BaseModel):
    """User model for MongoDB users collection"""
    
    def __init__(self):
        super().__init__('users')
        
        # Required fields
        self.user_id: str = None
        self.username: str = None
        self.email: str = None
        self.role: str = "user"  # admin, manager, user, viewer
        
        # Optional fields
        self.first_name: str = None
        self.last_name: str = None
        self.password_hash: str = None  # For demo purposes - in production use proper auth
        self.phone: str = None
        self.department: str = None
        self.position: str = None
        self.status: str = "active"  # active, inactive, suspended
        self.permissions: List[str] = []
        self.last_login: datetime = None
        self.login_count: int = 0
        self.profile_picture_url: str = None
        self.preferences: Dict[str, Any] = {}
        self.created_by: str = None
        self.last_modified_by: str = None
        
    def get_full_name(self) -> str:
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username or self.email
        
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        self.login_count += 1
        
    def has_permission(self, permission: str) -> bool:
        """Check if user has specific permission"""
        if self.role == "admin":
            return True
        return permission in self.permissions
        
    def validate(self) -> bool:
        """Validate user data"""
        if not self.user_id or not self.username or not self.email:
            return False
        if self.role not in ['admin', 'manager', 'user', 'viewer']:
            return False
        return True
    
    def before_save(self):
        """Set timestamps before saving"""
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        
        # Generate user_id if not provided
        if not self.user_id:
            self.user_id = f"USR_{int(now.timestamp())}"
            
        # Set default preferences
        if not self.preferences:
            self.preferences = {
                'theme': 'light',
                'notifications': True,
                'language': 'en'
            } 
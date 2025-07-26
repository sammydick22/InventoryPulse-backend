"""
Base model class for MongoDB documents
"""
from datetime import datetime
from bson import ObjectId
from typing import Dict, Any, Optional
import structlog

logger = structlog.get_logger()


class BaseModel:
    """Base class for all MongoDB models"""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._id = None
        self.created_at = None
        self.updated_at = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert model to dictionary"""
        result = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_') and key != 'collection_name':
                if isinstance(value, ObjectId):
                    result[key] = str(value)
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = value
        return result
    
    def from_dict(self, data: Dict[str, Any]) -> 'BaseModel':
        """Create model from dictionary"""
        for key, value in data.items():
            if key == '_id' and isinstance(value, (str, ObjectId)):
                self._id = ObjectId(value) if isinstance(value, str) else value
            elif key in ['created_at', 'updated_at'] and isinstance(value, str):
                setattr(self, key, datetime.fromisoformat(value.replace('Z', '+00:00')))
            else:
                setattr(self, key, value)
        return self
    
    def validate(self) -> bool:
        """Validate model data - to be overridden by subclasses"""
        return True
    
    def before_save(self):
        """Hook called before saving - to be overridden by subclasses"""
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
    
    def generate_id(self, prefix: str = '') -> str:
        """Generate a unique ID with optional prefix"""
        from uuid import uuid4
        unique_part = str(uuid4()).replace('-', '').upper()[:8]
        return f"{prefix}{unique_part}" if prefix else unique_part
    
    @classmethod
    def get_required_fields(cls) -> list:
        """Get list of required fields - to be overridden by subclasses"""
        return []
    
    @classmethod
    def get_unique_fields(cls) -> list:
        """Get list of unique fields - to be overridden by subclasses"""
        return [] 
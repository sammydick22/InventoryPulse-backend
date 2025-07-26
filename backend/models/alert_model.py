"""
Alert model for inventory alerts and notifications
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
import structlog

from backend.models.base_model import BaseModel

logger = structlog.get_logger()


class Alert(BaseModel):
    """Alert model for MongoDB alerts collection"""
    
    def __init__(self):
        super().__init__('alerts')
        
        # Required fields
        self.alert_id: str = None
        self.type: str = None  # low_stock, overstock, expiring, price_change, delivery_delay
        self.severity: str = "medium"  # low, medium, high, critical
        self.title: str = None
        self.message: str = None
        self.status: str = "active"  # active, acknowledged, resolved, dismissed
        
        # Optional fields
        self.product_id: str = None
        self.supplier_id: str = None
        self.order_id: str = None
        self.threshold_value: float = None
        self.current_value: float = None
        self.category: str = None
        self.action_required: bool = True
        self.acknowledged_at: datetime = None
        self.acknowledged_by: str = None
        self.resolved_at: datetime = None
        self.resolved_by: str = None
        self.auto_generated: bool = True
        self.tags: List[str] = []
        self.metadata: Dict[str, Any] = {}
        self.created_by: str = None
        
    def acknowledge(self, user_id: str):
        """Acknowledge the alert"""
        self.status = "acknowledged"
        self.acknowledged_at = datetime.utcnow()
        self.acknowledged_by = user_id
        
    def resolve(self, user_id: str):
        """Resolve the alert"""
        self.status = "resolved"
        self.resolved_at = datetime.utcnow()
        self.resolved_by = user_id
        
    def dismiss(self):
        """Dismiss the alert"""
        self.status = "dismissed"
        
    def validate(self) -> bool:
        """Validate alert data"""
        if not self.alert_id or not self.type or not self.title:
            return False
        if self.severity not in ['low', 'medium', 'high', 'critical']:
            return False
        return True
    
    def before_save(self):
        """Set timestamps before saving"""
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        
        # Generate alert_id if not provided
        if not self.alert_id:
            self.alert_id = f"ALT_{int(now.timestamp())}" 
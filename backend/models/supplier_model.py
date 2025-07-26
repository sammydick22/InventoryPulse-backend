"""
Supplier model for vendor/supplier management
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
import structlog

from backend.models.base_model import BaseModel

logger = structlog.get_logger()


class Supplier(BaseModel):
    """Supplier model for MongoDB suppliers collection"""
    
    def __init__(self):
        super().__init__('suppliers')
        
        # Required fields
        self.supplier_id: str = None
        self.name: str = None
        self.contact_email: str = None
        self.contact_phone: str = None
        
        # Optional fields
        self.company_name: str = None
        self.address: Dict[str, str] = {}
        self.contact_person: str = None
        self.website: str = None
        self.tax_id: str = None
        self.payment_terms: str = None
        self.currency: str = "USD"
        self.lead_time_days: int = 7
        self.minimum_order_value: float = 0.0
        self.discount_rate: float = 0.0
        self.rating: float = 0.0
        self.status: str = "active"  # active, inactive, suspended
        self.categories: List[str] = []
        self.notes: str = None
        self.created_by: str = None
        self.last_modified_by: str = None
        
    def validate(self) -> bool:
        """Validate supplier data"""
        if not self.supplier_id or not self.name:
            return False
        if not self.contact_email and not self.contact_phone:
            return False
        return True
    
    def before_save(self):
        """Set timestamps before saving"""
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        
        # Generate supplier_id if not provided
        if not self.supplier_id:
            self.supplier_id = f"SUP_{int(now.timestamp())}" 
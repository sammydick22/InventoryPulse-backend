"""
Order model for purchase order management
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
import structlog

from backend.models.base_model import BaseModel

logger = structlog.get_logger()


class Order(BaseModel):
    """Order model for MongoDB orders collection"""
    
    def __init__(self):
        super().__init__('purchase_orders')
        
        # Required fields
        self.order_id: str = None
        self.supplier_id: str = None
        self.order_date: datetime = None
        self.status: str = "pending"  # pending, confirmed, shipped, delivered, cancelled
        self.items: List[Dict[str, Any]] = []
        
        # Optional fields
        self.expected_delivery_date: datetime = None
        self.actual_delivery_date: datetime = None
        self.total_amount: float = 0.0
        self.currency: str = "USD"
        self.shipping_address: Dict[str, str] = {}
        self.billing_address: Dict[str, str] = {}
        self.payment_method: str = None
        self.payment_status: str = "pending"  # pending, paid, overdue
        self.tracking_number: str = None
        self.notes: str = None
        self.discount_percentage: float = 0.0
        self.tax_amount: float = 0.0
        self.shipping_cost: float = 0.0
        self.created_by: str = None
        self.last_modified_by: str = None
        
    def add_item(self, product_id: str, quantity: float, unit_price: float, product_name: str = None):
        """Add an item to the order"""
        item = {
            'product_id': product_id,
            'product_name': product_name,
            'quantity': quantity,
            'unit_price': unit_price,
            'total_price': quantity * unit_price
        }
        self.items.append(item)
        self._recalculate_total()
    
    def _recalculate_total(self):
        """Recalculate order total"""
        subtotal = sum(item.get('total_price', 0) for item in self.items)
        discount_amount = subtotal * (self.discount_percentage / 100)
        self.total_amount = subtotal - discount_amount + self.tax_amount + self.shipping_cost
        
    def validate(self) -> bool:
        """Validate order data"""
        if not self.order_id or not self.supplier_id:
            return False
        if not self.items:
            return False
        return True
    
    def before_save(self):
        """Set timestamps and calculations before saving"""
        now = datetime.utcnow()
        if not self.created_at:
            self.created_at = now
        self.updated_at = now
        
        # Generate order_id if not provided
        if not self.order_id:
            self.order_id = f"PO_{int(now.timestamp())}"
            
        # Set order_date if not provided
        if not self.order_date:
            self.order_date = now
            
        # Recalculate total
        self._recalculate_total() 
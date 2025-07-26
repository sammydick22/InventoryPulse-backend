"""
Product model for inventory management
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from bson import ObjectId
import structlog

from backend.models.base_model import BaseModel

logger = structlog.get_logger()


class Product(BaseModel):
    """Product model for MongoDB products collection"""
    
    def __init__(self):
        super().__init__('products')
        
        # Required fields
        self.product_id: str = None
        self.name: str = None
        self.category: str = None
        self.sku: str = None
        self.supplier_id: str = None
        self.current_stock: float = 0.0
        self.reorder_threshold: float = None
        self.reorder_quantity: float = None
        self.cost_price: float = None
        self.selling_price: float = None
        
        # Optional fields
        self.description: str = None
        self.subcategory: str = None
        self.barcode: str = None
        self.supplier_product_code: str = None
        self.reserved_stock: float = 0.0
        self.available_stock: float = 0.0
        self.max_stock_level: float = None
        self.currency: str = "USD"
        self.weight: float = None
        self.dimensions: Dict[str, float] = None
        self.warehouse_location: str = None
        self.storage_requirements: List[str] = []
        self.status: str = "active"
        self.created_by: str = None
        self.last_modified_by: str = None
        self.tags: List[str] = []
        self.seasonal: bool = False
        self.expiration_tracking: bool = False
        self.lot_tracking: bool = False
    
    @classmethod
    def get_required_fields(cls) -> List[str]:
        """Get list of required fields"""
        return [
            'product_id', 'name', 'category', 'sku', 'supplier_id',
            'current_stock', 'reorder_threshold', 'reorder_quantity',
            'cost_price', 'selling_price'
        ]
    
    @classmethod
    def get_unique_fields(cls) -> List[str]:
        """Get list of unique fields"""
        return ['product_id', 'sku']
    
    def validate(self) -> bool:
        """Validate product data"""
        errors = []
        
        # Check required fields
        for field in self.get_required_fields():
            if not getattr(self, field, None):
                errors.append(f"Missing required field: {field}")
        
        # Validate numeric fields
        if self.current_stock is not None and self.current_stock < 0:
            errors.append("Current stock cannot be negative")
        
        if self.reorder_threshold is not None and self.reorder_threshold <= 0:
            errors.append("Reorder threshold must be positive")
        
        if self.reorder_quantity is not None and self.reorder_quantity <= 0:
            errors.append("Reorder quantity must be positive")
        
        if self.cost_price is not None and self.cost_price < 0:
            errors.append("Cost price cannot be negative")
        
        if self.selling_price is not None and self.selling_price < 0:
            errors.append("Selling price cannot be negative")
        
        if (self.cost_price is not None and self.selling_price is not None and 
            self.selling_price < self.cost_price):
            errors.append("Selling price cannot be less than cost price")
        
        # Validate string lengths
        if self.name and len(self.name) > 200:
            errors.append("Product name cannot exceed 200 characters")
        
        if self.description and len(self.description) > 1000:
            errors.append("Description cannot exceed 1000 characters")
        
        if self.sku and len(self.sku) > 30:
            errors.append("SKU cannot exceed 30 characters")
        
        # Validate tags
        if self.tags and len(self.tags) > 20:
            errors.append("Cannot have more than 20 tags")
        
        if self.tags:
            for tag in self.tags:
                if len(tag) > 50:
                    errors.append("Tag cannot exceed 50 characters")
        
        # Validate status
        valid_statuses = ['active', 'discontinued', 'pending']
        if self.status and self.status not in valid_statuses:
            errors.append(f"Status must be one of: {', '.join(valid_statuses)}")
        
        if errors:
            logger.error("Product validation failed", errors=errors)
            return False
        
        return True
    
    def before_save(self):
        """Hook called before saving"""
        super().before_save()
        
        # Generate product_id if not provided
        if not self.product_id:
            self.product_id = self.generate_id('PRD-')
        
        # Calculate available stock
        self.available_stock = self.current_stock - (self.reserved_stock or 0)
        
        # Ensure tags is a list
        if not isinstance(self.tags, list):
            self.tags = []
        
        # Ensure storage_requirements is a list
        if not isinstance(self.storage_requirements, list):
            self.storage_requirements = []
    
    def update_stock(self, quantity_change: float, reason: str = None) -> bool:
        """Update current stock level"""
        new_stock = self.current_stock + quantity_change
        
        if new_stock < 0:
            logger.warning("Cannot reduce stock below zero", 
                         product_id=self.product_id,
                         current_stock=self.current_stock,
                         quantity_change=quantity_change)
            return False
        
        self.current_stock = new_stock
        self.available_stock = self.current_stock - (self.reserved_stock or 0)
        
        logger.info("Stock updated", 
                   product_id=self.product_id,
                   quantity_change=quantity_change,
                   new_stock=new_stock,
                   reason=reason)
        
        return True
    
    def is_low_stock(self) -> bool:
        """Check if product is below reorder threshold"""
        if not self.reorder_threshold:
            return False
        return self.current_stock <= self.reorder_threshold
    
    def get_stock_status(self) -> str:
        """Get stock status as string"""
        if self.current_stock <= 0:
            return "out_of_stock"
        elif self.is_low_stock():
            return "low_stock"
        elif self.max_stock_level and self.current_stock >= self.max_stock_level * 0.9:
            return "overstock"
        else:
            return "healthy"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with additional computed fields"""
        data = super().to_dict()
        data['stock_status'] = self.get_stock_status()
        data['is_low_stock'] = self.is_low_stock()
        return data 
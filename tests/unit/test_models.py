"""
Unit tests for model classes
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from backend.models.product_model import Product
from backend.models.base_model import BaseModel


class TestBaseModel:
    """Test cases for BaseModel"""
    
    def test_base_model_initialization(self):
        """Test base model initialization"""
        model = BaseModel('test_collection')
        assert model.collection_name == 'test_collection'
        assert model._id is None
        assert model.created_at is None
        assert model.updated_at is None
    
    def test_to_dict_conversion(self):
        """Test model to dictionary conversion"""
        model = BaseModel('test_collection')
        model.test_field = 'test_value'
        model.created_at = datetime(2025, 1, 1, 12, 0, 0)
        
        result = model.to_dict()
        assert 'test_field' in result
        assert result['test_field'] == 'test_value'
        assert 'created_at' in result
        assert result['created_at'] == '2025-01-01T12:00:00'
        assert 'collection_name' not in result
    
    def test_from_dict_creation(self):
        """Test model creation from dictionary"""
        data = {
            'test_field': 'test_value',
            'created_at': '2025-01-01T12:00:00'
        }
        
        model = BaseModel('test_collection')
        model.from_dict(data)
        
        assert model.test_field == 'test_value'
        assert isinstance(model.created_at, datetime)
    
    def test_generate_id(self):
        """Test ID generation"""
        model = BaseModel('test_collection')
        
        # Test without prefix
        id1 = model.generate_id()
        assert len(id1) == 8
        assert id1.isupper()
        
        # Test with prefix
        id2 = model.generate_id('TEST-')
        assert id2.startswith('TEST-')
        assert len(id2) == 13  # 5 chars prefix + 8 chars ID
    
    def test_before_save_hook(self):
        """Test before_save hook functionality"""
        model = BaseModel('test_collection')
        
        # First call should set created_at and updated_at
        model.before_save()
        assert model.created_at is not None
        assert model.updated_at is not None
        created_time = model.created_at
        
        # Second call should only update updated_at
        import time
        time.sleep(0.01)  # Small delay to ensure different timestamps
        model.before_save()
        assert model.created_at == created_time
        assert model.updated_at > created_time


class TestProductModel:
    """Test cases for Product model"""
    
    def test_product_initialization(self):
        """Test product model initialization"""
        product = Product()
        assert product.collection_name == 'products'
        assert product.current_stock == 0.0
        assert product.reserved_stock == 0.0
        assert product.available_stock == 0.0
        assert product.currency == 'USD'
        assert product.status == 'active'
        assert product.tags == []
        assert product.storage_requirements == []
        assert product.seasonal is False
        assert product.expiration_tracking is False
        assert product.lot_tracking is False
    
    def test_required_fields(self):
        """Test required fields definition"""
        required_fields = Product.get_required_fields()
        expected_fields = [
            'product_id', 'name', 'category', 'sku', 'supplier_id',
            'current_stock', 'reorder_threshold', 'reorder_quantity',
            'cost_price', 'selling_price'
        ]
        assert set(required_fields) == set(expected_fields)
    
    def test_unique_fields(self):
        """Test unique fields definition"""
        unique_fields = Product.get_unique_fields()
        expected_fields = ['product_id', 'sku']
        assert set(unique_fields) == set(expected_fields)
    
    def test_product_validation_success(self, sample_product_data):
        """Test successful product validation"""
        product = Product()
        product.from_dict(sample_product_data)
        assert product.validate() is True
    
    def test_product_validation_missing_required_fields(self):
        """Test validation failure with missing required fields"""
        product = Product()
        product.name = 'Test Product'
        # Missing other required fields
        
        assert product.validate() is False
    
    def test_product_validation_negative_stock(self, sample_product_data):
        """Test validation failure with negative stock"""
        product = Product()
        data = sample_product_data.copy()
        data['current_stock'] = -10
        product.from_dict(data)
        
        assert product.validate() is False
    
    def test_product_validation_zero_reorder_threshold(self, sample_product_data):
        """Test validation failure with zero reorder threshold"""
        product = Product()
        data = sample_product_data.copy()
        data['reorder_threshold'] = 0
        product.from_dict(data)
        
        assert product.validate() is False
    
    def test_product_validation_selling_price_less_than_cost(self, sample_product_data):
        """Test validation failure when selling price < cost price"""
        product = Product()
        data = sample_product_data.copy()
        data['cost_price'] = 20.00
        data['selling_price'] = 10.00
        product.from_dict(data)
        
        assert product.validate() is False
    
    def test_product_validation_string_length_limits(self, sample_product_data):
        """Test validation with string length limits"""
        product = Product()
        data = sample_product_data.copy()
        
        # Test name too long
        data['name'] = 'x' * 201
        product.from_dict(data)
        assert product.validate() is False
        
        # Test description too long
        data['name'] = 'Valid Name'
        data['description'] = 'x' * 1001
        product.from_dict(data)
        assert product.validate() is False
        
        # Test too many tags
        data['description'] = 'Valid description'
        data['tags'] = ['tag'] * 21
        product.from_dict(data)
        assert product.validate() is False
    
    def test_product_validation_invalid_status(self, sample_product_data):
        """Test validation with invalid status"""
        product = Product()
        data = sample_product_data.copy()
        data['status'] = 'invalid_status'
        product.from_dict(data)
        
        assert product.validate() is False
    
    def test_before_save_hook(self, sample_product_data):
        """Test product before_save hook"""
        product = Product()
        product.from_dict(sample_product_data)
        product.product_id = None  # Clear to test generation
        
        product.before_save()
        
        # Should generate product_id
        assert product.product_id is not None
        assert product.product_id.startswith('PRD-')
        
        # Should calculate available stock
        assert product.available_stock == product.current_stock - product.reserved_stock
        
        # Should ensure lists
        assert isinstance(product.tags, list)
        assert isinstance(product.storage_requirements, list)
    
    def test_update_stock_valid(self, sample_product_data):
        """Test valid stock update"""
        product = Product()
        product.from_dict(sample_product_data)
        initial_stock = product.current_stock
        
        # Test positive update
        result = product.update_stock(10, 'Test increase')
        assert result is True
        assert product.current_stock == initial_stock + 10
        assert product.available_stock == product.current_stock - product.reserved_stock
        
        # Test negative update
        result = product.update_stock(-5, 'Test decrease')
        assert result is True
        assert product.current_stock == initial_stock + 5
    
    def test_update_stock_invalid(self, sample_product_data):
        """Test invalid stock update (negative result)"""
        product = Product()
        product.from_dict(sample_product_data)
        product.current_stock = 10
        
        # Try to reduce below zero
        result = product.update_stock(-15, 'Invalid decrease')
        assert result is False
        assert product.current_stock == 10  # Should remain unchanged
    
    def test_is_low_stock(self, sample_product_data):
        """Test low stock detection"""
        product = Product()
        product.from_dict(sample_product_data)
        
        # Normal stock level
        product.current_stock = 50
        product.reorder_threshold = 20
        assert product.is_low_stock() is False
        
        # Low stock level
        product.current_stock = 15
        assert product.is_low_stock() is True
        
        # Exactly at threshold
        product.current_stock = 20
        assert product.is_low_stock() is True
        
        # No threshold set
        product.reorder_threshold = None
        assert product.is_low_stock() is False
    
    def test_get_stock_status(self, sample_product_data):
        """Test stock status calculation"""
        product = Product()
        product.from_dict(sample_product_data)
        
        # Out of stock
        product.current_stock = 0
        assert product.get_stock_status() == 'out_of_stock'
        
        # Low stock
        product.current_stock = 10
        product.reorder_threshold = 20
        assert product.get_stock_status() == 'low_stock'
        
        # Healthy stock
        product.current_stock = 50
        assert product.get_stock_status() == 'healthy'
        
        # Overstock
        product.current_stock = 190
        product.max_stock_level = 200
        assert product.get_stock_status() == 'overstock'
    
    def test_to_dict_with_computed_fields(self, sample_product_data):
        """Test to_dict includes computed fields"""
        product = Product()
        product.from_dict(sample_product_data)
        
        result = product.to_dict()
        
        # Should include computed fields
        assert 'stock_status' in result
        assert 'is_low_stock' in result
        assert result['stock_status'] == product.get_stock_status()
        assert result['is_low_stock'] == product.is_low_stock() 
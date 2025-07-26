"""
Global pytest configuration and fixtures
"""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime

# Add the backend directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_db():
    """Mock database connection"""
    mock_db = Mock()
    mock_db.products = Mock()
    mock_db.suppliers = Mock()
    mock_db.alerts = Mock()
    mock_db.orders = Mock()
    return mock_db

@pytest.fixture
def mock_snowflake_connection():
    """Mock Snowflake connection"""
    mock_conn = Mock()
    mock_cursor = Mock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []
    mock_cursor.description = []
    return mock_conn

@pytest.fixture
def sample_product():
    """Sample product data for testing"""
    return {
        '_id': 'sample_id',
        'product_id': 'PROD001',
        'name': 'Sample Product',
        'current_stock': 50,
        'max_stock': 100,
        'reorder_point': 20,
        'supplier': 'Sample Supplier',
        'category': 'Electronics',
        'unit_cost': 10.0,
        'last_updated': datetime.utcnow()
    }

@pytest.fixture
def sample_supplier():
    """Sample supplier data for testing"""
    return {
        'name': 'Sample Supplier',
        'contact_email': 'supplier@example.com',
        'phone': '+1-555-0123',
        'on_time_delivery_rate': 95.0,
        'quality_rating': 4.5,
        'cost_competitiveness': 85.0,
        'lead_time_days': 7
    }

@pytest.fixture
def sample_alert():
    """Sample alert data for testing"""
    return {
        'alert_id': 'alert_001',
        'alert_type': 'low_stock',
        'product_id': 'PROD001',
        'title': 'Low Stock Alert',
        'message': 'Product PROD001 is running low',
        'severity': 'high',
        'status': 'active',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow()
    }

@pytest.fixture(autouse=True)
def mock_external_services():
    """Auto-mock external services to prevent actual API calls during tests"""
    with patch('backend.services.ai_forecasting_service.get_snowflake_connection') as mock_snowflake, \
         patch('backend.services.mcp_service.get_snowflake_connection') as mock_snowflake2, \
         patch('backend.services.db_service.get_db') as mock_db_service:
        
        # Setup default mock returns
        mock_snowflake.return_value = None
        mock_snowflake2.return_value = None
        mock_db_service.return_value = Mock()
        
        yield {
            'snowflake': mock_snowflake,
            'snowflake2': mock_snowflake2,
            'db': mock_db_service
        }

@pytest.fixture
def mock_minimax_api():
    """Mock MiniMax API responses"""
    return {
        "status": "success",
        "content": """
        {
            "forecast": {
                "daily_demand": 12.5,
                "total_demand": 375.0,
                "confidence_level": "high",
                "trend": "increasing"
            },
            "insights": ["Test insight"],
            "recommendations": ["Test recommendation"]
        }
        """
    }

# Test markers
def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external services"
    ) 
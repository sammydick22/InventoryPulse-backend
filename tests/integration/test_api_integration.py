"""
Integration tests for API endpoints
"""
import pytest
import json
from unittest.mock import Mock, patch


class TestAPIIntegration:
    """Integration tests for API functionality"""
    
    def test_api_documentation_available(self, client):
        """Test that API documentation is accessible"""
        response = client.get('/api/docs/')
        # Flask-RESTX should provide Swagger UI
        assert response.status_code in [200, 302, 308]  # May redirect
    
    def test_health_check_integration(self, client):
        """Test complete health check workflow"""
        with patch('backend.services.db_service.get_db') as mock_get_db:
            mock_db = Mock()
            mock_db.command.return_value = True
            mock_get_db.return_value = mock_db

            # Redis removed for hackathon - not needed
            
            # Test health endpoint
            response = client.get('/api/system/health')
            assert response.status_code == 200
            
            health_data = json.loads(response.data)
            assert health_data['status'] == 'ok'
            
            # Test stats endpoint
            mock_collection = Mock()
            mock_collection.count_documents.return_value = 5
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_db.command.return_value = {'dataSize': 1024, 'indexSize': 512}
            
            response = client.get('/api/system/stats')
            assert response.status_code == 200
            
            stats_data = json.loads(response.data)
            assert 'database_stats' in stats_data
    
    def test_api_endpoints_structure(self, client):
        """Test that all major API endpoints are accessible"""
        endpoints = [
            '/api/auth/login',
            '/api/auth/status',
            '/api/products/',
            '/api/suppliers/',
            '/api/orders/purchase',
            '/api/users/',
            '/api/alerts/',
            '/api/system/health',
            '/api/system/stats'
        ]
        
        for endpoint in endpoints:
            if endpoint in ['/api/auth/login']:
                # POST endpoints
                response = client.post(endpoint)
            else:
                # GET endpoints
                response = client.get(endpoint)
            
            # Should not return 404 or 500
            assert response.status_code not in [404, 500]
            assert response.status_code < 500  # No server errors
    
    def test_json_content_type(self, client):
        """Test that API endpoints return JSON"""
        response = client.get('/api/system/health')
        assert response.status_code == 200
        assert 'application/json' in response.content_type
        
        # Should be valid JSON
        data = json.loads(response.data)
        assert isinstance(data, dict)
    
    def test_error_response_format(self, client):
        """Test that error responses follow consistent format"""
        response = client.get('/api/nonexistent')
        assert response.status_code == 404
        
        error_data = json.loads(response.data)
        assert 'error' in error_data
        assert 'status_code' in error_data
        assert error_data['status_code'] == 404
    
    def test_product_crud_flow(self, client):
        """Test basic product CRUD operations (placeholders)"""
        # Get products list
        response = client.get('/api/products/')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'products' in data
        
        # Create product (placeholder)
        product_data = {
            'name': 'Integration Test Product',
            'category': 'Test Category',
            'sku': 'INT-TEST-001'
        }
        response = client.post('/api/products/',
                             data=json.dumps(product_data),
                             content_type='application/json')
        assert response.status_code == 200
        
        # Get specific product (placeholder)
        response = client.get('/api/products/TEST-PRODUCT-001')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'product_id' in data


class TestFrontendBackendIntegration:
    """Test integration points between frontend and backend"""
    
    def test_cors_configuration(self, client):
        """Test CORS headers for frontend integration"""
        # Simulate preflight request
        response = client.options('/api/system/health')
        # Should not fail (exact CORS behavior depends on configuration)
        assert response.status_code in [200, 204, 405]  # 405 if OPTIONS not explicitly handled
        
        # Regular request should work
        response = client.get('/api/system/health')
        assert response.status_code == 200
    
    def test_api_base_structure(self, client):
        """Test that API follows expected structure for frontend consumption"""
        # Health check should return expected structure
        response = client.get('/api/system/health')
        data = json.loads(response.data)
        
        expected_keys = ['status', 'timestamp', 'version', 'dependencies']
        for key in expected_keys:
            assert key in data
        
        # Dependencies should include expected services
        deps = data['dependencies']
        expected_deps = ['mongodb', 'temporal', 'minimax', 'snowflake']
        for dep in expected_deps:
            assert dep in deps
    
    def test_placeholder_api_consistency(self, client):
        """Test that placeholder APIs return consistent structure"""
        placeholder_endpoints = [
            '/api/products/',
            '/api/suppliers/',
            '/api/users/',
            '/api/alerts/'
        ]
        
        for endpoint in placeholder_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200
            
            data = json.loads(response.data)
            assert 'status' in data
            assert data['status'] == 'placeholder'
            assert 'message' in data


class TestErrorIntegration:
    """Test error handling integration"""
    
    def test_application_error_handling(self, client):
        """Test that application handles errors gracefully"""
        # Test invalid endpoint
        response = client.get('/api/invalid/endpoint')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'error' in data
        assert isinstance(data['error'], str)
    
    def test_method_not_allowed(self, client):
        """Test method not allowed handling"""
        # Try POST on GET-only endpoint
        response = client.post('/api/system/health')
        assert response.status_code == 405  # Method Not Allowed
    
    def test_large_payload_handling(self, client):
        """Test handling of large payloads"""
        # Create a large JSON payload
        large_data = {'data': 'x' * 10000}  # 10KB of data
        
        response = client.post('/api/products/',
                             data=json.dumps(large_data),
                             content_type='application/json')
        
        # Should handle gracefully (not crash)
        assert response.status_code < 500 
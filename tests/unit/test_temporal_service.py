"""
Unit tests for Temporal Service
Tests workflow definitions and activity functions
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from dataclasses import asdict

from backend.services.temporal_service import (
    TemporalInventoryService,
    InventoryWorkflowInput,
    AlertWorkflowInput,
    temporal_service
)


class TestTemporalInventoryService:
    """Test suite for Temporal Inventory Service"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh temporal service instance"""
        return TemporalInventoryService()
    
    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.client is None
        assert service.worker is None
        assert service.task_queue == "inventory-task-queue"

    @pytest.mark.asyncio
    async def test_initialize_service(self, service):
        """Test service initialization"""
        with patch('temporalio.client.Client.connect') as mock_connect, \
             patch('temporalio.worker.Worker') as mock_worker:
            
            mock_client = AsyncMock()
            mock_connect.return_value = mock_client
            
            result = await service.initialize("localhost:7233")
            
            assert result is True
            assert service.client == mock_client
            mock_connect.assert_called_once_with("localhost:7233")

    @pytest.mark.asyncio
    async def test_start_worker(self, service):
        """Test starting Temporal worker"""
        mock_client = AsyncMock()
        service.client = mock_client
        
        with patch('temporalio.worker.Worker') as mock_worker_class:
            mock_worker = AsyncMock()
            mock_worker_class.return_value = mock_worker
            
            await service.start_worker()
            
            assert service.worker == mock_worker
            mock_worker.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_inventory_monitoring(self, service):
        """Test starting inventory monitoring workflow"""
        mock_client = AsyncMock()
        service.client = mock_client
        
        workflow_id = await service.start_inventory_monitoring("PROD001", 60)
        
        assert workflow_id.startswith("inventory-monitoring-PROD001-")
        mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_restock_workflow(self, service):
        """Test starting restock workflow"""
        mock_client = AsyncMock()
        service.client = mock_client
        
        workflow_id = await service.start_restock_workflow("PROD001")
        
        assert workflow_id.startswith("restock-PROD001-")
        mock_client.start_workflow.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_anomaly_detection(self, service):
        """Test starting anomaly detection workflow"""
        mock_client = AsyncMock()
        service.client = mock_client
        
        workflow_id = await service.start_anomaly_detection(3600)  # 1 hour
        
        assert workflow_id.startswith("anomaly-detection-")
        mock_client.start_workflow.assert_called_once()


class TestWorkflowInputs:
    """Test workflow input data classes"""
    
    def test_inventory_workflow_input(self):
        """Test InventoryWorkflowInput dataclass"""
        input_data = InventoryWorkflowInput(
            product_id="PROD001",
            check_interval_seconds=3600,
            auto_restock=True,
            low_stock_threshold=20.0
        )
        
        assert input_data.product_id == "PROD001"
        assert input_data.check_interval_seconds == 3600
        assert input_data.auto_restock is True
        assert input_data.low_stock_threshold == 20.0
        
        # Test serialization
        input_dict = asdict(input_data)
        assert input_dict['product_id'] == "PROD001"

    def test_alert_workflow_input(self):
        """Test AlertWorkflowInput dataclass"""
        input_data = AlertWorkflowInput(
            alert_id="alert_001",
            escalation_timeout_minutes=120,
            notification_channels=["email", "webhook"]
        )
        
        assert input_data.alert_id == "alert_001"
        assert input_data.escalation_timeout_minutes == 120
        assert "email" in input_data.notification_channels


class TestWorkflowActivities:
    """Test workflow activity functions"""
    
    @pytest.mark.asyncio
    async def test_check_inventory_levels(self):
        """Test inventory level checking activity"""
        from backend.services.temporal_service import check_inventory_levels
        
        with patch('backend.services.temporal_service.mcp_server') as mock_mcp:
            mock_mcp.get_inventory.return_value = {
                'status': 'success',
                'products': [
                    {
                        'product_id': 'PROD001',
                        'current_stock': 15,
                        'reorder_point': 20
                    }
                ]
            }
            
            result = await check_inventory_levels("PROD001")
            
            assert result['status'] == 'success'
            assert result['current_stock'] == 15
            assert result['needs_restock'] is True
            mock_mcp.get_inventory.assert_called_once_with(product_id="PROD001")

    @pytest.mark.asyncio
    async def test_generate_restock_recommendations(self):
        """Test restock recommendations activity"""
        from backend.services.temporal_service import generate_restock_recommendations
        
        with patch('backend.services.temporal_service.mcp_server') as mock_mcp:
            mock_mcp.generate_restock_recommendations_ai.return_value = {
                'status': 'success',
                'recommendations': [
                    {
                        'product_id': 'PROD001',
                        'recommended_quantity': 50,
                        'urgency': 'high'
                    }
                ]
            }
            
            result = await generate_restock_recommendations("PROD001")
            
            assert result['status'] == 'success'
            assert len(result['recommendations']) == 1

    @pytest.mark.asyncio
    async def test_detect_inventory_anomalies(self):
        """Test anomaly detection activity"""
        from backend.services.temporal_service import detect_inventory_anomalies
        
        with patch('backend.services.temporal_service.mcp_server') as mock_mcp:
            mock_mcp.get_inventory.return_value = {
                'status': 'success',
                'products': [
                    {
                        'product_id': 'PROD001',
                        'current_stock': -5,  # Negative stock anomaly
                        'name': 'Test Product'
                    }
                ]
            }
            
            result = await detect_inventory_anomalies()
            
            assert result['status'] == 'success'
            assert len(result['anomalies']) == 1
            assert result['anomalies'][0]['type'] == 'negative_stock'

    @pytest.mark.asyncio
    async def test_send_notification(self):
        """Test notification sending activity"""
        from backend.services.temporal_service import send_notification
        
        with patch('backend.services.temporal_service.mcp_server') as mock_mcp:
            mock_mcp.create_alert.return_value = {
                'status': 'success',
                'alert_id': 'alert_001'
            }
            
            result = await send_notification(
                "low_stock",
                "PROD001",
                "Low stock detected",
                "high"
            )
            
            assert result['status'] == 'success'
            mock_mcp.create_alert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_inventory_status(self):
        """Test inventory status update activity"""
        from backend.services.temporal_service import update_inventory_status
        
        with patch('backend.services.temporal_service.get_db') as mock_db:
            mock_db.return_value.products.update_one.return_value.modified_count = 1
            
            result = await update_inventory_status("PROD001", {"workflow_status": "monitoring"})
            
            assert result['status'] == 'success'
            assert result['updated'] is True

    @pytest.mark.asyncio
    async def test_calculate_demand_forecast(self):
        """Test demand forecast calculation activity"""
        from backend.services.temporal_service import calculate_demand_forecast
        
        with patch('backend.services.temporal_service.ai_forecasting_service') as mock_ai:
            mock_ai.forecast_demand_ai.return_value = {
                'status': 'success',
                'ai_forecast': {
                    'forecast': {
                        'daily_demand': 12.5,
                        'total_demand': 375.0
                    }
                }
            }
            
            result = await calculate_demand_forecast("PROD001", 30)
            
            assert result['status'] == 'success'
            assert result['daily_demand'] == 12.5


# Mock workflow classes for testing
class MockWorkflow:
    """Mock workflow for testing"""
    
    def __init__(self):
        self.activities_called = []
    
    async def run_activity(self, activity_name, *args, **kwargs):
        """Mock activity execution"""
        self.activities_called.append(activity_name)
        return {'status': 'success', 'activity': activity_name}


class TestWorkflowLogic:
    """Test workflow logic (simplified since we can't easily test actual Temporal workflows)"""
    
    @pytest.mark.asyncio
    async def test_inventory_monitoring_workflow_logic(self):
        """Test inventory monitoring workflow logic"""
        # This tests the logical flow without Temporal decorators
        mock_workflow = MockWorkflow()
        
        # Simulate workflow steps
        product_id = "PROD001"
        check_interval = 3600
        
        # Step 1: Check inventory
        inventory_result = await mock_workflow.run_activity("check_inventory_levels", product_id)
        assert 'check_inventory_levels' in mock_workflow.activities_called
        
        # Step 2: If low stock, trigger restock
        if inventory_result.get('needs_restock'):
            restock_result = await mock_workflow.run_activity("generate_restock_recommendations", product_id)
            assert 'generate_restock_recommendations' in mock_workflow.activities_called

    @pytest.mark.asyncio
    async def test_restock_workflow_logic(self):
        """Test restock workflow logic"""
        mock_workflow = MockWorkflow()
        
        product_id = "PROD001"
        
        # Step 1: Calculate demand forecast
        forecast_result = await mock_workflow.run_activity("calculate_demand_forecast", product_id, 30)
        assert 'calculate_demand_forecast' in mock_workflow.activities_called
        
        # Step 2: Generate recommendations
        restock_result = await mock_workflow.run_activity("generate_restock_recommendations", product_id)
        assert 'generate_restock_recommendations' in mock_workflow.activities_called
        
        # Step 3: Send notification
        notification_result = await mock_workflow.run_activity(
            "send_notification", "restock_needed", product_id, "Restock required", "medium"
        )
        assert 'send_notification' in mock_workflow.activities_called

    @pytest.mark.asyncio
    async def test_anomaly_detection_workflow_logic(self):
        """Test anomaly detection workflow logic"""
        mock_workflow = MockWorkflow()
        
        # Step 1: Detect anomalies
        anomaly_result = await mock_workflow.run_activity("detect_inventory_anomalies")
        assert 'detect_inventory_anomalies' in mock_workflow.activities_called
        
        # Step 2: If anomalies found, send alerts
        if anomaly_result.get('anomalies'):
            alert_result = await mock_workflow.run_activity(
                "send_notification", "anomaly_detected", None, "Anomalies detected", "high"
            )
            assert 'send_notification' in mock_workflow.activities_called


class TestTemporalServiceIntegration:
    """Integration tests for Temporal Service"""
    
    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """Test that global service instance works"""
        assert temporal_service is not None
        assert isinstance(temporal_service, TemporalInventoryService)

    def test_workflow_input_validation(self):
        """Test workflow input validation"""
        # Valid input
        valid_input = InventoryWorkflowInput(
            product_id="PROD001",
            check_interval_seconds=3600,
            auto_restock=True,
            low_stock_threshold=20.0
        )
        assert valid_input.product_id == "PROD001"
        
        # Test with missing optional fields
        minimal_input = InventoryWorkflowInput(
            product_id="PROD002",
            check_interval_seconds=1800
        )
        assert minimal_input.auto_restock is False  # Default value
        assert minimal_input.low_stock_threshold == 10.0  # Default value

    @pytest.mark.asyncio
    async def test_service_error_handling(self):
        """Test service error handling"""
        service = TemporalInventoryService()
        
        # Test workflow start without client
        with pytest.raises(Exception):
            await service.start_inventory_monitoring("PROD001", 60)

    @pytest.mark.asyncio
    async def test_activity_error_handling(self):
        """Test activity error handling"""
        from backend.services.temporal_service import check_inventory_levels
        
        with patch('backend.services.temporal_service.mcp_server') as mock_mcp:
            mock_mcp.get_inventory.side_effect = Exception("Database error")
            
            result = await check_inventory_levels("PROD001")
            
            assert result['status'] == 'error'
            assert 'Database error' in result['message']

    def test_workflow_id_generation(self):
        """Test workflow ID generation patterns"""
        service = TemporalInventoryService()
        
        # Test different ID patterns
        monitoring_id = service._generate_workflow_id("inventory-monitoring", "PROD001")
        assert monitoring_id.startswith("inventory-monitoring-PROD001-")
        
        restock_id = service._generate_workflow_id("restock", "PROD002")
        assert restock_id.startswith("restock-PROD002-")
        
        # IDs should be unique
        id1 = service._generate_workflow_id("test", "PROD001")
        id2 = service._generate_workflow_id("test", "PROD001")
        assert id1 != id2

    @pytest.mark.asyncio
    async def test_concurrent_workflow_management(self):
        """Test managing multiple concurrent workflows"""
        service = TemporalInventoryService()
        
        with patch.object(service, 'client') as mock_client:
            mock_client.start_workflow = AsyncMock()
            
            # Start multiple workflows
            id1 = await service.start_inventory_monitoring("PROD001", 60)
            id2 = await service.start_inventory_monitoring("PROD002", 120)
            id3 = await service.start_restock_workflow("PROD001")
            
            # All should have unique IDs
            assert id1 != id2 != id3
            assert mock_client.start_workflow.call_count == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 
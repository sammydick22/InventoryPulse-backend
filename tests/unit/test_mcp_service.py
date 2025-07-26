"""
Unit tests for Enhanced MCP Service
Tests all 24 standardized tools for AI agent interactions
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from dataclasses import asdict

from backend.services.mcp_service import InventoryMCPServer, mcp_server


class TestInventoryMCPServer:
    """Test suite for Enhanced MCP Service"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh MCP service instance"""
        return InventoryMCPServer()
    
    @pytest.fixture
    def mock_products(self):
        """Mock product data"""
        return [
            {
                '_id': 'mock_id_1',
                'product_id': 'PROD001',
                'name': 'Test Product 1',
                'current_stock': 50,
                'max_stock': 100,
                'reorder_point': 20,
                'supplier': 'Supplier A',
                'category': 'Electronics',
                'unit_cost': 10.0,
                'last_updated': datetime.utcnow()
            },
            {
                '_id': 'mock_id_2',
                'product_id': 'PROD002',
                'name': 'Test Product 2',
                'current_stock': 5,
                'max_stock': 80,
                'reorder_point': 15,
                'supplier': 'Supplier B',
                'category': 'Electronics',
                'unit_cost': 15.0,
                'last_updated': datetime.utcnow()
            }
        ]

    def test_service_initialization(self, service):
        """Test service initializes with all tools"""
        assert len(service.tools) == 24
        
        # Check core tools
        core_tools = ['get_inventory', 'check_low_stock', 'forecast_demand', 'recommend_restock']
        for tool in core_tools:
            assert tool in service.tools
        
        # Check AI-powered tools
        ai_tools = ['analyze_inventory_health', 'get_predictive_insights', 'optimize_inventory_levels']
        for tool in ai_tools:
            assert tool in service.tools
        
        # Check monitoring tools
        monitoring_tools = ['start_monitoring', 'get_active_alerts', 'acknowledge_alert']
        for tool in monitoring_tools:
            assert tool in service.tools
        
        # Check analytics tools
        analytics_tools = ['generate_dashboard', 'benchmark_performance']
        for tool in analytics_tools:
            assert tool in service.tools

    # Core Inventory Tools Tests
    
    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_get_inventory_single_product(self, mock_db, service, mock_products):
        """Test getting inventory for a single product"""
        mock_db.return_value.products.find.return_value.limit.return_value = [mock_products[0]]
        
        result = await service.get_inventory(product_id='PROD001')
        
        assert result['status'] == 'success'
        assert result['inventory_count'] == 1
        assert result['products'][0]['product_id'] == 'PROD001'
        assert result['products'][0]['_id'] == 'mock_id_1'

    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_get_inventory_all_products(self, mock_db, service, mock_products):
        """Test getting all inventory"""
        mock_db.return_value.products.find.return_value.limit.return_value = mock_products
        
        result = await service.get_inventory()
        
        assert result['status'] == 'success'
        assert result['inventory_count'] == 2
        assert len(result['products']) == 2

    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_check_low_stock(self, mock_db, service):
        """Test low stock checking"""
        mock_db.return_value.products.aggregate.return_value = [
            {
                '_id': 'mock_id',
                'product_id': 'PROD002',
                'current_stock': 5,
                'stock_percentage': 6.25
            }
        ]
        
        result = await service.check_low_stock(threshold_percentage=20.0)
        
        assert result['status'] == 'success'
        assert result['low_stock_count'] == 1
        assert result['threshold_percentage'] == 20.0

    @patch('backend.services.mcp_service.get_snowflake_connection')
    @pytest.mark.asyncio
    async def test_forecast_demand_success(self, mock_snowflake, service):
        """Test demand forecasting"""
        # Mock Snowflake connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            ('2024-01-01', 10, 100.0),
            ('2024-01-02', 15, 150.0)
        ]
        mock_cursor.description = [('SNAPSHOT_DATE',), ('QUANTITY_SOLD',), ('REVENUE',)]
        mock_snowflake.return_value = mock_conn
        
        result = await service.forecast_demand('PROD001', days_ahead=30)
        
        assert result['status'] == 'success'
        assert result['product_id'] == 'PROD001'
        assert result['forecast_period_days'] == 30
        assert 'forecast' in result

    @patch('backend.services.mcp_service.get_db')
    @patch.object(InventoryMCPServer, 'check_low_stock')
    @patch.object(InventoryMCPServer, 'forecast_demand')
    @pytest.mark.asyncio
    async def test_recommend_restock(self, mock_forecast, mock_low_stock, mock_db, service):
        """Test restock recommendations"""
        # Setup mocks
        mock_low_stock.return_value = {
            'status': 'success',
            'items': [{'product_id': 'PROD001', 'current_stock': 5, 'safety_stock': 10}]
        }
        mock_forecast.return_value = {
            'status': 'success',
            'forecast': {'total_demand': 100.0}
        }
        
        result = await service.recommend_restock()
        
        assert result['status'] == 'success'
        assert 'recommendations' in result

    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_create_alert(self, mock_db, service):
        """Test alert creation"""
        mock_db.return_value.alerts.insert_one.return_value.inserted_id = 'mock_alert_id'
        
        result = await service.create_alert(
            alert_type='low_stock',
            product_id='PROD001',
            message='Product running low',
            severity='high'
        )
        
        assert result['status'] == 'success'
        assert result['alert_created']['type'] == 'low_stock'
        assert result['alert_created']['severity'] == 'high'

    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_update_inventory(self, mock_db, service):
        """Test inventory update"""
        mock_db.return_value.products.update_one.return_value.matched_count = 1
        mock_db.return_value.products.update_one.return_value.modified_count = 1
        
        result = await service.update_inventory('PROD001', 75, 'Restock received')
        
        assert result['status'] == 'success'
        assert result['product_id'] == 'PROD001'
        assert result['new_stock'] == 75
        assert result['updated_count'] == 1

    # Enhanced AI-Powered Tools Tests
    
    @patch('backend.services.mcp_service.advanced_analytics_service')
    @pytest.mark.asyncio
    async def test_analyze_inventory_health(self, mock_analytics, service):
        """Test inventory health analysis"""
        mock_analytics.calculate_inventory_health_score.return_value = {
            'overall_score': 85.0,
            'status': 'good'
        }
        mock_analytics.calculate_inventory_kpis.return_value = []
        mock_analytics.generate_ai_insights.return_value = []
        
        result = await service.analyze_inventory_health()
        
        assert result['status'] == 'success'
        assert 'health_analysis' in result
        assert 'key_metrics' in result

    @patch('backend.services.mcp_service.ai_forecasting_service')
    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_get_predictive_insights_single_product(self, mock_db, mock_ai, service):
        """Test predictive insights for single product"""
        mock_ai.forecast_demand_ai.return_value = {
            'status': 'success',
            'ai_forecast': {'forecast': {'risk_assessment': 'medium'}}
        }
        
        result = await service.get_predictive_insights(product_id='PROD001')
        
        assert result['status'] == 'success'
        assert result['prediction_type'] == 'single_product'
        assert result['product_id'] == 'PROD001'

    @patch('backend.services.mcp_service.ai_forecasting_service')
    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_get_predictive_insights_multi_product(self, mock_db, mock_ai, service, mock_products):
        """Test predictive insights for multiple products"""
        mock_db.return_value.products.find.return_value.limit.return_value = mock_products
        mock_ai.forecast_demand_ai.return_value = {
            'status': 'success',
            'ai_forecast': {'forecast': {'risk_assessment': 'medium'}}
        }
        
        result = await service.get_predictive_insights()
        
        assert result['status'] == 'success'
        assert result['prediction_type'] == 'multi_product'
        assert 'predictions' in result

    @patch('backend.services.mcp_service.get_db')
    @patch.object(InventoryMCPServer, 'forecast_demand')
    @pytest.mark.asyncio
    async def test_optimize_inventory_levels(self, mock_forecast, mock_db, service, mock_products):
        """Test inventory level optimization"""
        mock_db.return_value.products.find.return_value.limit.return_value = mock_products
        mock_forecast.return_value = {
            'status': 'success',
            'forecast': {'total_demand': 100.0}
        }
        
        result = await service.optimize_inventory_levels()
        
        assert result['status'] == 'success'
        assert 'optimizations' in result

    @patch.object(InventoryMCPServer, 'forecast_demand')
    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_calculate_safety_stock(self, mock_db, mock_forecast, service):
        """Test safety stock calculation"""
        mock_db.return_value.products.find_one.return_value = {
            'product_id': 'PROD001',
            'reorder_point': 10,
            'lead_time_days': 7
        }
        mock_forecast.return_value = {
            'status': 'success',
            'forecast': {'daily_demand': 5.0}
        }
        
        result = await service.calculate_safety_stock('PROD001', service_level=0.95)
        
        assert result['status'] == 'success'
        assert 'safety_stock_calculation' in result
        assert result['safety_stock_calculation']['service_level'] == 0.95

    @patch.object(InventoryMCPServer, 'get_sales_analytics')
    @pytest.mark.asyncio
    async def test_analyze_demand_patterns_single_product(self, mock_analytics, service):
        """Test demand pattern analysis for single product"""
        mock_analytics.return_value = {
            'status': 'success',
            'analytics': [
                {
                    'PRODUCT_ID': 'PROD001',
                    'TOTAL_QUANTITY': 100,
                    'AVG_DAILY_QUANTITY': 3.33
                }
            ]
        }
        
        result = await service.analyze_demand_patterns(product_id='PROD001')
        
        assert result['status'] == 'success'
        assert result['product_id'] == 'PROD001'
        assert 'demand_analysis' in result

    @patch('backend.services.mcp_service.advanced_analytics_service')
    @pytest.mark.asyncio
    async def test_get_supplier_performance(self, mock_analytics, service):
        """Test supplier performance analysis"""
        mock_analytics.analyze_supplier_performance.return_value = [
            Mock(supplier_name='Supplier A', risk_level='low')
        ]
        
        result = await service.get_supplier_performance('Supplier A')
        
        assert result['status'] == 'success'
        assert 'supplier' in result

    @patch.object(InventoryMCPServer, 'forecast_demand')
    @patch.object(InventoryMCPServer, 'get_inventory')
    @pytest.mark.asyncio
    async def test_simulate_scenarios_demand_spike(self, mock_inventory, mock_forecast, service):
        """Test demand spike scenario simulation"""
        mock_forecast.return_value = {
            'status': 'success',
            'forecast': {'daily_demand': 10.0}
        }
        mock_inventory.return_value = {
            'products': [{'current_stock': 50}]
        }
        
        parameters = {
            'product_id': 'PROD001',
            'spike_factor': 2.0,
            'duration_days': 7
        }
        
        result = await service.simulate_scenarios('demand_spike', parameters)
        
        assert result['status'] == 'success'
        assert result['scenario'] == 'demand_spike'
        assert 'simulation_results' in result

    @patch('backend.services.mcp_service.advanced_analytics_service')
    @pytest.mark.asyncio
    async def test_get_inventory_kpis(self, mock_analytics, service):
        """Test inventory KPIs retrieval"""
        from backend.services.advanced_analytics_service import InventoryKPI
        mock_analytics.calculate_inventory_kpis.return_value = [
            InventoryKPI("Test KPI", 85.0, "%", "up", 5.0, 80.0, "normal")
        ]
        
        result = await service.get_inventory_kpis(30)
        
        assert result['status'] == 'success'
        assert result['period_days'] == 30
        assert len(result['kpis']) == 1

    # Real-time Monitoring Tools Tests
    
    @patch('backend.services.mcp_service.temporal_service')
    @pytest.mark.asyncio
    async def test_start_monitoring(self, mock_temporal, service):
        """Test starting monitoring workflow"""
        mock_temporal.start_inventory_monitoring.return_value = 'workflow_123'
        
        result = await service.start_monitoring('PROD001', 60)
        
        assert result['status'] == 'success'
        assert result['monitoring_started'] is True
        assert result['workflow_id'] == 'workflow_123'

    @pytest.mark.asyncio
    async def test_stop_monitoring(self, service):
        """Test stopping monitoring workflow"""
        result = await service.stop_monitoring('workflow_123')
        
        assert result['status'] == 'success'
        assert result['monitoring_stopped'] is True

    @patch('backend.services.mcp_service.real_time_alerting_service')
    @pytest.mark.asyncio
    async def test_get_active_alerts(self, mock_alerting, service):
        """Test getting active alerts"""
        mock_alerting.get_active_alerts.return_value = []
        
        result = await service.get_active_alerts()
        
        assert result['status'] == 'success'
        assert 'active_alerts' in result

    @patch('backend.services.mcp_service.real_time_alerting_service')
    @pytest.mark.asyncio
    async def test_acknowledge_alert(self, mock_alerting, service):
        """Test acknowledging an alert"""
        mock_alerting.acknowledge_alert.return_value = True
        
        result = await service.acknowledge_alert('alert_123', 'user_1')
        
        assert result['status'] == 'success'
        assert result['acknowledged'] is True

    @patch('backend.services.mcp_service.real_time_alerting_service')
    @pytest.mark.asyncio
    async def test_resolve_alert(self, mock_alerting, service):
        """Test resolving an alert"""
        mock_alerting.resolve_alert.return_value = True
        
        result = await service.resolve_alert('alert_123', 'user_1', 'Fixed the issue')
        
        assert result['status'] == 'success'
        assert result['resolved'] is True

    # Advanced Analytics Tools Tests
    
    @patch('backend.services.mcp_service.advanced_analytics_service')
    @pytest.mark.asyncio
    async def test_generate_dashboard(self, mock_analytics, service):
        """Test dashboard generation"""
        mock_analytics.generate_inventory_dashboard.return_value = {
            'timestamp': datetime.utcnow().isoformat(),
            'kpis': []
        }
        
        result = await service.generate_dashboard(30)
        
        assert result['status'] == 'success'
        assert 'dashboard' in result

    @patch.object(InventoryMCPServer, 'generate_dashboard')
    @patch.object(InventoryMCPServer, 'get_inventory_kpis')
    @pytest.mark.asyncio
    async def test_export_analytics_report(self, mock_kpis, mock_dashboard, service):
        """Test analytics report export"""
        mock_dashboard.return_value = {'status': 'success', 'dashboard': {}}
        mock_kpis.return_value = {'status': 'success', 'kpis': []}
        
        result = await service.export_analytics_report('summary', 'json')
        
        assert result['status'] == 'success'
        assert result['format'] == 'json'
        assert 'report' in result

    @patch.object(InventoryMCPServer, 'get_inventory_kpis')
    @pytest.mark.asyncio
    async def test_benchmark_performance(self, mock_kpis, service):
        """Test performance benchmarking"""
        from backend.services.advanced_analytics_service import InventoryKPI
        mock_kpis.return_value = {
            'status': 'success',
            'kpis': [
                asdict(InventoryKPI("Inventory Turnover Rate", 5.2, "times/period", "up", 5.0, 6.0, "normal"))
            ]
        }
        
        result = await service.benchmark_performance('turnover_rate', 'industry')
        
        assert result['status'] == 'success'
        assert result['metric'] == 'turnover_rate'
        assert 'performance_level' in result

    # Tool Schema Tests
    
    def test_get_tool_schemas(self, service):
        """Test tool schema generation"""
        schemas = service.get_tool_schemas()
        
        assert len(schemas) == 24
        
        # Check core tools
        assert 'get_inventory' in schemas
        assert 'forecast_demand' in schemas
        
        # Check AI tools
        assert 'analyze_inventory_health' in schemas
        assert 'get_predictive_insights' in schemas
        
        # Check monitoring tools
        assert 'start_monitoring' in schemas
        assert 'get_active_alerts' in schemas
        
        # Check analytics tools
        assert 'generate_dashboard' in schemas
        assert 'benchmark_performance' in schemas
        
        # Verify schema structure
        for tool_name, schema in schemas.items():
            assert 'description' in schema
            assert 'parameters' in schema
            assert 'type' in schema['parameters']
            assert schema['parameters']['type'] == 'object'

    def test_tool_schema_required_fields(self, service):
        """Test tool schemas have required fields where appropriate"""
        schemas = service.get_tool_schemas()
        
        # forecast_demand should require product_id
        forecast_schema = schemas['forecast_demand']
        assert 'required' in forecast_schema['parameters']
        assert 'product_id' in forecast_schema['parameters']['required']
        
        # calculate_safety_stock should require product_id
        safety_stock_schema = schemas['calculate_safety_stock']
        assert 'required' in safety_stock_schema['parameters']
        assert 'product_id' in safety_stock_schema['parameters']['required']

    # Error Handling Tests
    
    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_get_inventory_error_handling(self, mock_db, service):
        """Test error handling in get_inventory"""
        mock_db.side_effect = Exception("Database error")
        
        result = await service.get_inventory()
        
        assert result['status'] == 'error'
        assert 'Database error' in result['message']

    @patch('backend.services.mcp_service.get_db')
    @pytest.mark.asyncio
    async def test_update_inventory_product_not_found(self, mock_db, service):
        """Test update inventory with non-existent product"""
        mock_db.return_value.products.update_one.return_value.matched_count = 0
        
        result = await service.update_inventory('NONEXISTENT', 50)
        
        assert result['status'] == 'error'
        assert 'not found' in result['message']

    @pytest.mark.asyncio
    async def test_simulate_scenarios_unknown_type(self, service):
        """Test scenario simulation with unknown type"""
        result = await service.simulate_scenarios('unknown_scenario', {})
        
        assert result['status'] == 'error'
        assert 'Unknown scenario type' in result['message']

    @pytest.mark.asyncio
    async def test_simulate_scenarios_missing_parameters(self, service):
        """Test scenario simulation with missing parameters"""
        result = await service.simulate_scenarios('demand_spike', {})
        
        assert result['status'] == 'error'
        assert 'product_id required' in result['message']


# Integration tests
class TestInventoryMCPServerIntegration:
    """Integration tests for MCP Service"""
    
    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """Test that global service instance works"""
        assert mcp_server is not None
        assert isinstance(mcp_server, InventoryMCPServer)
        assert len(mcp_server.tools) == 24

    def test_all_tools_are_callable(self):
        """Test that all tools in the service are callable"""
        for tool_name, tool_func in mcp_server.tools.items():
            assert callable(tool_func), f"Tool {tool_name} is not callable"

    def test_tool_names_match_schemas(self):
        """Test that tool names match schema keys"""
        tools = set(mcp_server.tools.keys())
        schemas = set(mcp_server.get_tool_schemas().keys())
        
        assert tools == schemas, f"Mismatch: tools={tools}, schemas={schemas}"

    @pytest.mark.asyncio
    async def test_tool_execution_basic(self):
        """Test basic tool execution without mocks"""
        # Test a simple tool that doesn't require external dependencies
        with patch('backend.services.mcp_service.get_db') as mock_db:
            mock_db.return_value.products.find.return_value.limit.return_value = []
            
            result = await mcp_server.tools['get_inventory']()
            assert 'status' in result

    def test_tool_categorization(self):
        """Test that tools are properly categorized"""
        schemas = mcp_server.get_tool_schemas()
        
        # Core inventory tools
        core_tools = ['get_inventory', 'check_low_stock', 'forecast_demand', 'recommend_restock', 
                     'get_sales_analytics', 'create_alert', 'update_inventory', 'get_supplier_info']
        
        # AI-powered tools
        ai_tools = ['analyze_inventory_health', 'get_predictive_insights', 'optimize_inventory_levels',
                   'calculate_safety_stock', 'analyze_demand_patterns', 'get_supplier_performance',
                   'simulate_scenarios', 'get_inventory_kpis']
        
        # Monitoring tools
        monitoring_tools = ['start_monitoring', 'stop_monitoring', 'get_active_alerts',
                          'acknowledge_alert', 'resolve_alert']
        
        # Analytics tools
        analytics_tools = ['generate_dashboard', 'export_analytics_report', 'benchmark_performance']
        
        all_expected_tools = core_tools + ai_tools + monitoring_tools + analytics_tools
        
        assert len(all_expected_tools) == 24
        assert set(all_expected_tools) == set(schemas.keys())


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 
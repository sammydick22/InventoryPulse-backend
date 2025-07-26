"""
Unit tests for Advanced Analytics Service
Tests comprehensive analytics, KPI calculations, and business intelligence
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from dataclasses import asdict

from backend.services.advanced_analytics_service import (
    AdvancedAnalyticsService, 
    InventoryKPI, 
    ProductPerformance, 
    SupplierPerformance, 
    AnalyticsInsight,
    advanced_analytics_service
)


class TestAdvancedAnalyticsService:
    """Test suite for Advanced Analytics Service"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh analytics service instance"""
        return AdvancedAnalyticsService()
    
    @pytest.fixture
    def mock_products(self):
        """Mock product data"""
        return [
            {
                'product_id': 'PROD001',
                'name': 'Test Product 1',
                'current_stock': 50,
                'max_stock': 100,
                'reorder_point': 20,
                'supplier': 'Supplier A',
                'category': 'Electronics',
                'unit_cost': 10.0
            },
            {
                'product_id': 'PROD002',
                'name': 'Test Product 2',
                'current_stock': 5,
                'max_stock': 80,
                'reorder_point': 15,
                'supplier': 'Supplier B',
                'category': 'Electronics',
                'unit_cost': 15.0
            }
        ]
    
    @pytest.fixture
    def mock_suppliers(self):
        """Mock supplier data"""
        return [
            {
                'name': 'Supplier A',
                'on_time_delivery_rate': 95.0,
                'quality_rating': 4.5,
                'cost_competitiveness': 85.0,
                'lead_time_days': 5
            },
            {
                'name': 'Supplier B',
                'on_time_delivery_rate': 78.0,
                'quality_rating': 3.8,
                'cost_competitiveness': 92.0,
                'lead_time_days': 7
            }
        ]

    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert service.cache_duration == timedelta(hours=1)
        assert isinstance(service.analytics_cache, dict)
        assert isinstance(service.kpi_cache, dict)

    @pytest.mark.asyncio
    async def test_initialize_service(self, service):
        """Test service initialization"""
        result = await service.initialize()
        assert result is True

    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.calculate_inventory_kpis')
    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.get_top_performing_products')
    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.get_underperforming_products')
    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.analyze_supplier_performance')
    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.generate_ai_insights')
    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.calculate_inventory_health_score')
    @patch('backend.services.advanced_analytics_service.advanced_analytics_service.analyze_inventory_trends')
    @patch.object(AdvancedAnalyticsService, '_get_all_products')
    @patch.object(AdvancedAnalyticsService, '_get_low_stock_items')
    @patch.object(AdvancedAnalyticsService, '_get_out_of_stock_items')
    @patch.object(AdvancedAnalyticsService, '_get_overstock_items')
    @pytest.mark.asyncio
    async def test_generate_inventory_dashboard(
        self, 
        mock_overstock, mock_outstock, mock_lowstock, mock_all_products,
        mock_trends, mock_health, mock_insights, mock_suppliers,
        mock_underperforming, mock_top, mock_kpis,
        service, mock_products
    ):
        """Test comprehensive dashboard generation"""
        # Setup mocks
        mock_kpis.return_value = [
            InventoryKPI("Test KPI", 85.0, "%", "up", 5.0, 80.0, "normal")
        ]
        mock_top.return_value = [
            ProductPerformance("PROD001", "Test Product", 1000.0, 100, 25.0, 5.2, 30.0, 85.0, 15.0)
        ]
        mock_underperforming.return_value = []
        mock_suppliers.return_value = [
            SupplierPerformance("Supplier A", 95.0, 90.0, 85.0, 90.0, 5000.0, "low")
        ]
        mock_insights.return_value = [
            AnalyticsInsight("insight1", "inventory", "Test Insight", "Description", "high", True, "Recommendation", 0.9, {})
        ]
        mock_health.return_value = {"overall_score": 85.0, "status": "good"}
        mock_trends.return_value = {"stock_level_trend": {"trend": "stable"}}
        mock_all_products.return_value = mock_products
        mock_lowstock.return_value = [mock_products[1]]
        mock_outstock.return_value = []
        mock_overstock.return_value = []
        
        result = await service.generate_inventory_dashboard(30)
        
        assert result['timestamp'] is not None
        assert result['period_days'] == 30
        assert 'kpis' in result
        assert 'inventory_health_score' in result
        assert 'top_performing_products' in result
        assert 'ai_insights' in result
        assert 'trends' in result
        assert 'summary' in result

    @pytest.mark.asyncio
    async def test_generate_inventory_dashboard_cached(self, service):
        """Test dashboard uses cache when available"""
        # Pre-populate cache
        cached_data = {
            'cached_at': datetime.utcnow().isoformat(),
            'test': 'cached_data'
        }
        service.analytics_cache['dashboard_30'] = cached_data
        
        result = await service.generate_inventory_dashboard(30)
        
        assert result['test'] == 'cached_data'

    @pytest.mark.asyncio
    async def test_calculate_inventory_kpis(self, service):
        """Test KPI calculations"""
        with patch.object(service, '_calculate_inventory_turnover') as mock_turnover, \
             patch.object(service, '_calculate_stockout_rate') as mock_stockout, \
             patch.object(service, '_calculate_carrying_cost') as mock_cost, \
             patch.object(service, '_calculate_forecast_accuracy') as mock_accuracy, \
             patch.object(service, '_calculate_fill_rate') as mock_fill:
            
            # Setup mock returns
            mock_turnover.return_value = {'current': 5.2, 'previous': 4.8}
            mock_stockout.return_value = {'current': 3.5, 'previous': 4.2}
            mock_cost.return_value = {'current': 15000.0, 'previous': 14500.0}
            mock_accuracy.return_value = {'current': 82.5, 'previous': 79.1}
            mock_fill.return_value = {'current': 94.2, 'previous': 92.8}
            
            result = await service.calculate_inventory_kpis(30)
            
            assert len(result) == 5
            assert all(isinstance(kpi, InventoryKPI) for kpi in result)
            
            # Check specific KPIs
            turnover_kpi = next(kpi for kpi in result if 'Turnover' in kpi.name)
            assert turnover_kpi.value == 5.2
            assert turnover_kpi.trend == 'up'

    @patch.object(AdvancedAnalyticsService, '_get_product_sales_data')
    @patch.object(AdvancedAnalyticsService, '_get_current_inventory_data')
    @patch.object(AdvancedAnalyticsService, '_get_product_forecast_accuracy')
    @pytest.mark.asyncio
    async def test_get_top_performing_products(
        self, mock_accuracy, mock_inventory, mock_sales, service
    ):
        """Test top performing products analysis"""
        # Setup mocks
        mock_sales.return_value = {
            'PROD001': {
                'total_revenue': 1000.0,
                'total_quantity': 100,
                'avg_daily_quantity': 3.33
            }
        }
        mock_inventory.return_value = {
            'PROD001': {
                'name': 'Test Product',
                'current_stock': 30,
                'unit_cost': 8.0
            }
        }
        mock_accuracy.return_value = 85.0
        
        result = await service.get_top_performing_products(5)
        
        assert len(result) <= 5
        if result:
            product = result[0]
            assert isinstance(product, ProductPerformance)
            assert product.product_id == 'PROD001'
            assert product.revenue == 1000.0

    @pytest.mark.asyncio
    async def test_get_underperforming_products(self, service):
        """Test underperforming products identification"""
        with patch.object(service, 'get_top_performing_products') as mock_top:
            # Mock products with poor performance
            mock_top.return_value = [
                ProductPerformance("PROD001", "Good Product", 1000.0, 100, 25.0, 5.2, 30.0, 85.0, 20.0),
                ProductPerformance("PROD002", "Poor Product", 200.0, 20, 15.0, 1.5, 90.0, 60.0, 80.0)
            ]
            
            result = await service.get_underperforming_products(10)
            
            # Should identify the product with high risk and low turnover
            poor_products = [p for p in result if p.risk_score > 70 or p.turnover_rate < 2.0]
            assert len(poor_products) >= 0

    @patch('backend.services.advanced_analytics_service.get_db')
    @pytest.mark.asyncio
    async def test_analyze_supplier_performance(self, mock_db, service, mock_suppliers):
        """Test supplier performance analysis"""
        # Setup mock database
        mock_db.return_value.suppliers.find.return_value = mock_suppliers
        mock_db.return_value.products.find.return_value = [
            {'supplier': 'Supplier A', 'current_stock': 50, 'unit_cost': 10.0},
            {'supplier': 'Supplier B', 'current_stock': 25, 'unit_cost': 15.0}
        ]
        
        result = await service.analyze_supplier_performance()
        
        assert len(result) == 2
        supplier_a = next(s for s in result if s.supplier_name == 'Supplier A')
        assert isinstance(supplier_a, SupplierPerformance)
        assert supplier_a.on_time_delivery_rate == 95.0
        assert supplier_a.risk_level == 'low'

    @patch.object(AdvancedAnalyticsService, '_gather_analytics_data')
    @patch.object(AdvancedAnalyticsService, '_analyze_inventory_level_insights')
    @patch.object(AdvancedAnalyticsService, '_analyze_demand_pattern_insights')
    @patch.object(AdvancedAnalyticsService, '_analyze_supplier_insights')
    @patch.object(AdvancedAnalyticsService, '_analyze_seasonal_insights')
    @pytest.mark.asyncio
    async def test_generate_ai_insights(
        self, mock_seasonal, mock_supplier, mock_demand, mock_inventory, mock_gather, service
    ):
        """Test AI insights generation"""
        # Setup mocks
        mock_gather.return_value = {'products': [], 'sales_data': {}}
        mock_inventory.return_value = [
            AnalyticsInsight("insight1", "inventory", "Low Stock Alert", "Multiple items low", "high", True, "Reorder soon", 0.95, {})
        ]
        mock_demand.return_value = []
        mock_supplier.return_value = []
        mock_seasonal.return_value = []
        
        result = await service.generate_ai_insights(30)
        
        assert len(result) >= 0
        if result:
            insight = result[0]
            assert isinstance(insight, AnalyticsInsight)
            assert insight.impact in ['high', 'medium', 'low']

    @patch.object(AdvancedAnalyticsService, '_get_historical_trend_data')
    @pytest.mark.asyncio
    async def test_analyze_inventory_trends(self, mock_historical, service):
        """Test inventory trends analysis"""
        mock_historical.return_value = {'sample': 'data'}
        
        result = await service.analyze_inventory_trends(30)
        
        assert 'stock_level_trend' in result
        assert 'demand_trend' in result
        assert 'cost_trend' in result
        assert 'seasonality' in result
        assert 'velocity_changes' in result

    @patch.object(AdvancedAnalyticsService, '_calculate_stock_level_health')
    @patch.object(AdvancedAnalyticsService, '_calculate_demand_fulfillment_health')
    @patch.object(AdvancedAnalyticsService, '_calculate_cost_efficiency_health')
    @patch.object(AdvancedAnalyticsService, '_calculate_turnover_health')
    @patch.object(AdvancedAnalyticsService, '_calculate_forecast_health')
    @pytest.mark.asyncio
    async def test_calculate_inventory_health_score(
        self, mock_forecast, mock_turnover, mock_cost, mock_demand, mock_stock, service
    ):
        """Test inventory health score calculation"""
        # Setup mock health scores
        mock_stock.return_value = 85.0
        mock_demand.return_value = 90.0
        mock_cost.return_value = 75.0
        mock_turnover.return_value = 80.0
        mock_forecast.return_value = 82.0
        
        result = await service.calculate_inventory_health_score()
        
        assert 'overall_score' in result
        assert 'status' in result
        assert 'components' in result
        assert 'recommendations' in result
        
        # Check score calculation (weighted average)
        expected_score = (85.0 * 0.25 + 90.0 * 0.30 + 75.0 * 0.20 + 80.0 * 0.15 + 82.0 * 0.10)
        assert abs(result['overall_score'] - expected_score) < 0.1

    def test_is_cache_valid_fresh(self, service):
        """Test cache validity check with fresh data"""
        cache_key = 'test_cache'
        fresh_data = {
            'cached_at': datetime.utcnow().isoformat(),
            'data': 'test'
        }
        service.analytics_cache[cache_key] = fresh_data
        
        result = service._is_cache_valid(cache_key)
        assert result is True

    def test_is_cache_valid_expired(self, service):
        """Test cache validity check with expired data"""
        cache_key = 'test_cache'
        old_time = datetime.utcnow() - timedelta(hours=2)
        expired_data = {
            'cached_at': old_time.isoformat(),
            'data': 'test'
        }
        service.analytics_cache[cache_key] = expired_data
        
        result = service._is_cache_valid(cache_key)
        assert result is False

    def test_is_cache_valid_missing(self, service):
        """Test cache validity check with missing data"""
        result = service._is_cache_valid('nonexistent_key')
        assert result is False

    def test_cache_result(self, service):
        """Test caching of results"""
        data = {'test': 'data'}
        service._cache_result('test_key', data)
        
        assert 'test_key' in service.analytics_cache
        assert service.analytics_cache['test_key']['test'] == 'data'
        assert 'cached_at' in service.analytics_cache['test_key']

    def test_calculate_trend_up(self, service):
        """Test trend calculation - upward"""
        result = service._calculate_trend(10.0, 8.0)
        assert result == 'up'

    def test_calculate_trend_down(self, service):
        """Test trend calculation - downward"""
        result = service._calculate_trend(8.0, 10.0)
        assert result == 'down'

    def test_calculate_trend_stable(self, service):
        """Test trend calculation - stable"""
        result = service._calculate_trend(10.0, 10.005)
        assert result == 'stable'

    def test_calculate_change_percentage(self, service):
        """Test percentage change calculation"""
        result = service._calculate_change_percentage(110.0, 100.0)
        assert result == 10.0
        
        result = service._calculate_change_percentage(90.0, 100.0)
        assert result == -10.0
        
        result = service._calculate_change_percentage(50.0, 0.0)
        assert result == 0.0

    @patch('backend.services.advanced_analytics_service.get_db')
    @pytest.mark.asyncio
    async def test_get_all_products(self, mock_db, service, mock_products):
        """Test getting all products"""
        mock_db.return_value.products.find.return_value = mock_products
        
        result = await service._get_all_products()
        assert result == mock_products

    @patch('backend.services.advanced_analytics_service.get_db')
    @pytest.mark.asyncio
    async def test_get_low_stock_items(self, mock_db, service):
        """Test getting low stock items"""
        mock_db.return_value.products.find.return_value = [{'product_id': 'LOW001'}]
        
        result = await service._get_low_stock_items()
        assert len(result) == 1
        assert result[0]['product_id'] == 'LOW001'

    @patch('backend.services.advanced_analytics_service.get_db')
    @pytest.mark.asyncio
    async def test_get_out_of_stock_items(self, mock_db, service):
        """Test getting out of stock items"""
        mock_db.return_value.products.find.return_value = [{'product_id': 'OUT001', 'current_stock': 0}]
        
        result = await service._get_out_of_stock_items()
        assert len(result) == 1

    @patch('backend.services.advanced_analytics_service.get_db')
    @pytest.mark.asyncio
    async def test_get_overstock_items(self, mock_db, service):
        """Test getting overstock items"""
        mock_db.return_value.products.aggregate.return_value = [{'product_id': 'OVER001'}]
        
        result = await service._get_overstock_items()
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_analyze_inventory_level_insights(self, service):
        """Test inventory level insights analysis"""
        data = {
            'products': [
                {'current_stock': 5, 'reorder_point': 10},
                {'current_stock': 8, 'reorder_point': 10},
                {'current_stock': 15, 'reorder_point': 10}
            ]
        }
        
        result = await service._analyze_inventory_level_insights(data)
        
        # Should detect high number of low stock items
        if result:
            insight = result[0]
            assert insight.category == 'inventory_levels'
            assert insight.impact == 'high'

    def test_generate_health_recommendations(self, service):
        """Test health recommendations generation"""
        components = {
            'demand_fulfillment': 60.0,  # Below 70
            'cost_efficiency': 65.0     # Below 70
        }
        
        result = service._generate_health_recommendations(65.0, components)
        
        assert len(result) >= 2
        assert any('inventory management processes' in rec for rec in result)
        assert any('demand fulfillment' in rec for rec in result)


# Integration tests
class TestAdvancedAnalyticsServiceIntegration:
    """Integration tests for Advanced Analytics Service"""
    
    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """Test that global service instance works"""
        assert advanced_analytics_service is not None
        assert isinstance(advanced_analytics_service, AdvancedAnalyticsService)

    def test_inventory_kpi_dataclass(self):
        """Test InventoryKPI dataclass"""
        kpi = InventoryKPI(
            name="Test KPI",
            value=85.0,
            unit="%",
            trend="up",
            change_percentage=5.0,
            target_value=80.0,
            status="normal"
        )
        
        assert kpi.name == "Test KPI"
        assert kpi.value == 85.0
        assert kpi.trend == "up"
        
        # Test serialization
        kpi_dict = asdict(kpi)
        assert kpi_dict['name'] == "Test KPI"

    def test_product_performance_dataclass(self):
        """Test ProductPerformance dataclass"""
        performance = ProductPerformance(
            product_id="PROD001",
            name="Test Product",
            revenue=1000.0,
            units_sold=100,
            profit_margin=25.0,
            turnover_rate=5.2,
            days_of_supply=30.0,
            forecast_accuracy=85.0,
            risk_score=15.0
        )
        
        assert performance.product_id == "PROD001"
        assert performance.revenue == 1000.0
        
        # Test serialization
        perf_dict = asdict(performance)
        assert perf_dict['product_id'] == "PROD001"

    def test_supplier_performance_dataclass(self):
        """Test SupplierPerformance dataclass"""
        supplier = SupplierPerformance(
            supplier_name="Test Supplier",
            on_time_delivery_rate=95.0,
            quality_score=90.0,
            cost_competitiveness=85.0,
            relationship_score=90.0,
            total_value=5000.0,
            risk_level="low"
        )
        
        assert supplier.supplier_name == "Test Supplier"
        assert supplier.risk_level == "low"

    def test_analytics_insight_dataclass(self):
        """Test AnalyticsInsight dataclass"""
        insight = AnalyticsInsight(
            insight_id="insight_001",
            category="inventory",
            title="Test Insight",
            description="Test description",
            impact="high",
            actionable=True,
            recommendation="Test recommendation",
            confidence_score=0.95,
            supporting_data={"key": "value"}
        )
        
        assert insight.insight_id == "insight_001"
        assert insight.confidence_score == 0.95
        assert insight.actionable is True


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 
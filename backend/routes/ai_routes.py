"""
AI and Analytics routes for InventoryPulse
Exposes enhanced AI forecasting, analytics, and MCP tools through REST API
"""

from flask_restx import Namespace, Resource, fields
from flask import request, current_app
import asyncio
import structlog

logger = structlog.get_logger(__name__)

ai_ns = Namespace('ai', description='AI and analytics endpoints')

# Response models for documentation
forecasting_model = ai_ns.model('ForecastingResponse', {
    'status': fields.String(description='Response status'),
    'product_id': fields.String(description='Product ID'),
    'forecast_period_days': fields.Integer(description='Forecast period in days'),
    'ai_forecast': fields.Raw(description='AI forecast data'),
    'timestamp': fields.String(description='Timestamp')
})

analytics_model = ai_ns.model('AnalyticsResponse', {
    'status': fields.String(description='Response status'),
    'dashboard': fields.Raw(description='Dashboard data'),
    'timestamp': fields.String(description='Timestamp')
})

health_model = ai_ns.model('HealthResponse', {
    'status': fields.String(description='Response status'),
    'health_analysis': fields.Raw(description='Health analysis data'),
    'timestamp': fields.String(description='Timestamp')
})

@ai_ns.route('/forecast/<string:product_id>')
class AIForecast(Resource):
    """AI-powered demand forecasting"""
    
    @ai_ns.doc('forecast_demand')
    @ai_ns.marshal_with(forecasting_model)
    def get(self, product_id):
        """Get AI demand forecast for a product"""
        try:
            from backend.services.ai_forecasting_service import ai_forecasting_service
            
            days_ahead = request.args.get('days_ahead', 30, type=int)
            
            # Run async function in event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    ai_forecasting_service.forecast_demand_ai(product_id, days_ahead)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Forecast API error", product_id=product_id, error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/analytics/dashboard')
class AnalyticsDashboard(Resource):
    """Advanced analytics dashboard"""
    
    @ai_ns.doc('generate_dashboard')
    @ai_ns.marshal_with(analytics_model)
    def get(self):
        """Generate comprehensive analytics dashboard"""
        try:
            from backend.services.advanced_analytics_service import advanced_analytics_service
            
            time_period = request.args.get('time_period', 30, type=int)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    advanced_analytics_service.generate_inventory_dashboard(time_period)
                )
                return {'status': 'success', 'dashboard': result, 'timestamp': result.get('timestamp')}
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Dashboard API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/health')
class InventoryHealth(Resource):
    """Inventory health analysis"""
    
    @ai_ns.doc('analyze_health')
    @ai_ns.marshal_with(health_model)
    def get(self):
        """Analyze overall inventory health"""
        try:
            from backend.services.mcp_service import mcp_server
            
            include_recommendations = request.args.get('include_recommendations', True, type=bool)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.analyze_inventory_health(include_recommendations)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Health analysis API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/insights')
class PredictiveInsights(Resource):
    """Predictive insights and recommendations"""
    
    @ai_ns.doc('get_insights')
    def get(self):
        """Get AI-powered predictive insights"""
        try:
            from backend.services.mcp_service import mcp_server
            
            product_id = request.args.get('product_id')
            days_ahead = request.args.get('days_ahead', 30, type=int)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.get_predictive_insights(product_id, days_ahead)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Insights API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/optimize')
class InventoryOptimization(Resource):
    """Inventory level optimization"""
    
    @ai_ns.doc('optimize_levels')
    def get(self):
        """Get inventory optimization recommendations"""
        try:
            from backend.services.mcp_service import mcp_server
            
            category = request.args.get('category')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.optimize_inventory_levels(category)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Optimization API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/safety-stock/<string:product_id>')
class SafetyStockCalculation(Resource):
    """Safety stock calculation"""
    
    @ai_ns.doc('calculate_safety_stock')
    def get(self, product_id):
        """Calculate optimal safety stock for a product"""
        try:
            from backend.services.mcp_service import mcp_server
            
            service_level = request.args.get('service_level', 0.95, type=float)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.calculate_safety_stock(product_id, service_level)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Safety stock API error", product_id=product_id, error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/scenarios/simulate')
class ScenarioSimulation(Resource):
    """Scenario simulation"""
    
    @ai_ns.doc('simulate_scenario')
    def post(self):
        """Simulate inventory scenarios"""
        try:
            from backend.services.mcp_service import mcp_server
            
            data = request.get_json()
            scenario_type = data.get('scenario_type')
            parameters = data.get('parameters', {})
            
            if not scenario_type:
                return {'status': 'error', 'message': 'scenario_type required'}, 400
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.simulate_scenarios(scenario_type, parameters)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Scenario simulation API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/kpis')
class InventoryKPIs(Resource):
    """Inventory Key Performance Indicators"""
    
    @ai_ns.doc('get_kpis')
    def get(self):
        """Get comprehensive inventory KPIs"""
        try:
            from backend.services.mcp_service import mcp_server
            
            period_days = request.args.get('period_days', 30, type=int)
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.get_inventory_kpis(period_days)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("KPIs API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/monitoring/start')
class StartMonitoring(Resource):
    """Start real-time monitoring"""
    
    @ai_ns.doc('start_monitoring')
    def post(self):
        """Start real-time monitoring for products"""
        try:
            from backend.services.mcp_service import mcp_server
            
            data = request.get_json()
            product_id = data.get('product_id')
            check_interval = data.get('check_interval_minutes', 60)
            
            if not product_id:
                return {'status': 'error', 'message': 'product_id required'}, 400
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.start_monitoring(product_id, check_interval)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Start monitoring API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/alerts')
class AlertManagement(Resource):
    """Alert management"""
    
    @ai_ns.doc('get_alerts')
    def get(self):
        """Get active alerts"""
        try:
            from backend.services.mcp_service import mcp_server
            
            product_id = request.args.get('product_id')
            severity = request.args.get('severity')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.get_active_alerts(product_id, severity)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Get alerts API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/alerts/<string:alert_id>/acknowledge')
class AlertAcknowledge(Resource):
    """Acknowledge alerts"""
    
    @ai_ns.doc('acknowledge_alert')
    def post(self, alert_id):
        """Acknowledge an alert"""
        try:
            from backend.services.mcp_service import mcp_server
            
            data = request.get_json()
            acknowledged_by = data.get('acknowledged_by')
            
            if not acknowledged_by:
                return {'status': 'error', 'message': 'acknowledged_by required'}, 400
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.acknowledge_alert(alert_id, acknowledged_by)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Acknowledge alert API error", alert_id=alert_id, error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/mcp/tools')
class MCPTools(Resource):
    """MCP tool schemas"""
    
    @ai_ns.doc('get_mcp_tools')
    def get(self):
        """Get available MCP tools and their schemas"""
        try:
            from backend.services.mcp_service import mcp_server
            
            schemas = mcp_server.get_tool_schemas()
            
            return {
                'status': 'success',
                'tools': schemas,
                'total_tools': len(schemas),
                'categories': {
                    'core_inventory': 8,
                    'ai_powered': 8,
                    'monitoring': 5,
                    'analytics': 3
                }
            }
            
        except Exception as e:
            logger.error("MCP tools API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500

@ai_ns.route('/benchmark')
class PerformanceBenchmark(Resource):
    """Performance benchmarking"""
    
    @ai_ns.doc('benchmark_performance')
    def get(self):
        """Benchmark inventory performance against industry standards"""
        try:
            from backend.services.mcp_service import mcp_server
            
            metric = request.args.get('metric', 'turnover_rate')
            benchmark_type = request.args.get('benchmark_type', 'industry')
            
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(
                    mcp_server.benchmark_performance(metric, benchmark_type)
                )
                return result
            finally:
                loop.close()
                
        except Exception as e:
            logger.error("Benchmark API error", error=str(e))
            return {'status': 'error', 'message': str(e)}, 500 
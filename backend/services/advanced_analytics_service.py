"""
Advanced Analytics and Insights Service for Inventory Management
Provides AI-powered analytics, trend analysis, KPI calculations, and business intelligence
"""

import asyncio
import structlog
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict
import json

from backend.services.db_service import get_db
from backend.services.snowflake_service import get_snowflake_connection
from backend.services.ai_forecasting_service import ai_forecasting_service
from backend.services.mcp_service import mcp_server

logger = structlog.get_logger(__name__)

@dataclass
class InventoryKPI:
    """Key Performance Indicator for inventory"""
    name: str
    value: float
    unit: str
    trend: str  # "up", "down", "stable"
    change_percentage: float
    target_value: Optional[float] = None
    status: str = "normal"  # "normal", "warning", "critical"

@dataclass
class ProductPerformance:
    """Product performance metrics"""
    product_id: str
    name: str
    revenue: float
    units_sold: int
    profit_margin: float
    turnover_rate: float
    days_of_supply: float
    forecast_accuracy: float
    risk_score: float

@dataclass
class SupplierPerformance:
    """Supplier performance metrics"""
    supplier_name: str
    on_time_delivery_rate: float
    quality_score: float
    cost_competitiveness: float
    relationship_score: float
    total_value: float
    risk_level: str

@dataclass
class AnalyticsInsight:
    """AI-generated business insight"""
    insight_id: str
    category: str
    title: str
    description: str
    impact: str  # "high", "medium", "low"
    actionable: bool
    recommendation: str
    confidence_score: float
    supporting_data: Dict[str, Any]

class AdvancedAnalyticsService:
    """Advanced analytics service with AI-powered insights"""
    
    def __init__(self):
        self.cache_duration = timedelta(hours=1)  # Cache results for 1 hour
        self.analytics_cache: Dict[str, Dict] = {}
        self.kpi_cache: Dict[str, List[InventoryKPI]] = {}
        
    async def initialize(self):
        """Initialize the analytics service"""
        try:
            logger.info("Advanced analytics service initialized")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize analytics service", error=str(e))
            return False
    
    # Main Analytics Functions
    
    async def generate_inventory_dashboard(self, time_period: int = 30) -> Dict[str, Any]:
        """Generate comprehensive inventory dashboard"""
        try:
            cache_key = f"dashboard_{time_period}"
            
            # Check cache
            if self._is_cache_valid(cache_key):
                return self.analytics_cache[cache_key]
            
            # Calculate KPIs
            kpis = await self.calculate_inventory_kpis(time_period)
            
            # Get top performers and underperformers
            top_products = await self.get_top_performing_products(limit=10)
            underperforming_products = await self.get_underperforming_products(limit=10)
            
            # Get supplier performance
            supplier_performance = await self.analyze_supplier_performance()
            
            # Generate AI insights
            ai_insights = await self.generate_ai_insights(time_period)
            
            # Calculate inventory health score
            health_score = await self.calculate_inventory_health_score()
            
            # Get trend analysis
            trends = await self.analyze_inventory_trends(time_period)
            
            dashboard_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "period_days": time_period,
                "kpis": [asdict(kpi) for kpi in kpis],
                "inventory_health_score": health_score,
                "top_performing_products": [asdict(p) for p in top_products],
                "underperforming_products": [asdict(p) for p in underperforming_products],
                "supplier_performance": [asdict(s) for s in supplier_performance],
                "ai_insights": [asdict(insight) for insight in ai_insights],
                "trends": trends,
                "summary": {
                    "total_products": len(await self._get_all_products()),
                    "low_stock_items": len(await self._get_low_stock_items()),
                    "out_of_stock_items": len(await self._get_out_of_stock_items()),
                    "overstock_items": len(await self._get_overstock_items())
                }
            }
            
            # Cache the result
            self._cache_result(cache_key, dashboard_data)
            
            return dashboard_data
            
        except Exception as e:
            logger.error("Failed to generate inventory dashboard", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def calculate_inventory_kpis(self, time_period: int = 30) -> List[InventoryKPI]:
        """Calculate key performance indicators"""
        try:
            kpis = []
            
            # Inventory Turnover Rate
            turnover_rate = await self._calculate_inventory_turnover(time_period)
            kpis.append(InventoryKPI(
                name="Inventory Turnover Rate",
                value=turnover_rate["current"],
                unit="times/period",
                trend=self._calculate_trend(turnover_rate["current"], turnover_rate["previous"]),
                change_percentage=self._calculate_change_percentage(turnover_rate["current"], turnover_rate["previous"]),
                target_value=6.0,
                status="normal" if turnover_rate["current"] >= 4.0 else "warning"
            ))
            
            # Stock-out Rate
            stockout_rate = await self._calculate_stockout_rate(time_period)
            kpis.append(InventoryKPI(
                name="Stock-out Rate",
                value=stockout_rate["current"],
                unit="%",
                trend=self._calculate_trend(stockout_rate["previous"], stockout_rate["current"]),  # Reversed - lower is better
                change_percentage=self._calculate_change_percentage(stockout_rate["current"], stockout_rate["previous"]),
                target_value=2.0,
                status="critical" if stockout_rate["current"] > 5.0 else ("warning" if stockout_rate["current"] > 2.0 else "normal")
            ))
            
            # Carrying Cost
            carrying_cost = await self._calculate_carrying_cost(time_period)
            kpis.append(InventoryKPI(
                name="Carrying Cost",
                value=carrying_cost["current"],
                unit="$",
                trend=self._calculate_trend(carrying_cost["previous"], carrying_cost["current"]),  # Reversed - lower is better
                change_percentage=self._calculate_change_percentage(carrying_cost["current"], carrying_cost["previous"]),
                target_value=carrying_cost["current"] * 0.8,
                status="warning" if carrying_cost["current"] > carrying_cost.get("target", 0) else "normal"
            ))
            
            # Forecast Accuracy
            forecast_accuracy = await self._calculate_forecast_accuracy(time_period)
            kpis.append(InventoryKPI(
                name="Forecast Accuracy",
                value=forecast_accuracy["current"],
                unit="%",
                trend=self._calculate_trend(forecast_accuracy["current"], forecast_accuracy["previous"]),
                change_percentage=self._calculate_change_percentage(forecast_accuracy["current"], forecast_accuracy["previous"]),
                target_value=85.0,
                status="normal" if forecast_accuracy["current"] >= 80.0 else "warning"
            ))
            
            # Fill Rate
            fill_rate = await self._calculate_fill_rate(time_period)
            kpis.append(InventoryKPI(
                name="Fill Rate",
                value=fill_rate["current"],
                unit="%",
                trend=self._calculate_trend(fill_rate["current"], fill_rate["previous"]),
                change_percentage=self._calculate_change_percentage(fill_rate["current"], fill_rate["previous"]),
                target_value=95.0,
                status="normal" if fill_rate["current"] >= 95.0 else ("warning" if fill_rate["current"] >= 90.0 else "critical")
            ))
            
            return kpis
            
        except Exception as e:
            logger.error("Failed to calculate KPIs", error=str(e))
            return []
    
    async def get_top_performing_products(self, limit: int = 10) -> List[ProductPerformance]:
        """Get top performing products based on multiple metrics"""
        try:
            # Get sales data from Snowflake
            sales_data = await self._get_product_sales_data(days_back=30)
            
            # Get current inventory data
            inventory_data = await self._get_current_inventory_data()
            
            # Calculate performance metrics for each product
            product_performances = []
            
            for product_id, sales in sales_data.items():
                inventory = inventory_data.get(product_id, {})
                
                # Calculate performance metrics
                revenue = sales.get("total_revenue", 0)
                units_sold = sales.get("total_quantity", 0)
                
                # Calculate turnover rate
                avg_inventory = inventory.get("current_stock", 1)
                turnover_rate = units_sold / avg_inventory if avg_inventory > 0 else 0
                
                # Calculate days of supply
                avg_daily_sales = sales.get("avg_daily_quantity", 0)
                days_of_supply = avg_inventory / avg_daily_sales if avg_daily_sales > 0 else float('inf')
                
                # Calculate profit margin (simplified)
                unit_cost = inventory.get("unit_cost", 0)
                avg_selling_price = revenue / units_sold if units_sold > 0 else 0
                profit_margin = ((avg_selling_price - unit_cost) / avg_selling_price * 100) if avg_selling_price > 0 else 0
                
                # Calculate risk score based on various factors
                risk_score = self._calculate_product_risk_score(inventory, sales)
                
                # Get forecast accuracy
                forecast_accuracy = await self._get_product_forecast_accuracy(product_id)
                
                performance = ProductPerformance(
                    product_id=product_id,
                    name=inventory.get("name", product_id),
                    revenue=revenue,
                    units_sold=units_sold,
                    profit_margin=profit_margin,
                    turnover_rate=turnover_rate,
                    days_of_supply=days_of_supply,
                    forecast_accuracy=forecast_accuracy,
                    risk_score=risk_score
                )
                
                product_performances.append(performance)
            
            # Sort by a composite score (revenue + turnover + low risk)
            product_performances.sort(
                key=lambda p: (p.revenue * 0.4 + p.turnover_rate * 0.3 + (100 - p.risk_score) * 0.3),
                reverse=True
            )
            
            return product_performances[:limit]
            
        except Exception as e:
            logger.error("Failed to get top performing products", error=str(e))
            return []
    
    async def get_underperforming_products(self, limit: int = 10) -> List[ProductPerformance]:
        """Get underperforming products that need attention"""
        try:
            all_products = await self.get_top_performing_products(limit=100)  # Get more for analysis
            
            # Filter for underperforming products
            underperforming = [
                p for p in all_products
                if (p.turnover_rate < 2.0 or p.days_of_supply > 60 or p.risk_score > 70)
            ]
            
            # Sort by risk score (highest first)
            underperforming.sort(key=lambda p: p.risk_score, reverse=True)
            
            return underperforming[:limit]
            
        except Exception as e:
            logger.error("Failed to get underperforming products", error=str(e))
            return []
    
    async def analyze_supplier_performance(self) -> List[SupplierPerformance]:
        """Analyze supplier performance metrics"""
        try:
            db = get_db()
            suppliers = list(db.suppliers.find())
            
            supplier_performances = []
            
            for supplier in suppliers:
                supplier_name = supplier.get("name", "Unknown")
                
                # Get products from this supplier
                supplier_products = list(db.products.find({"supplier": supplier_name}))
                
                # Calculate metrics
                total_value = sum(p.get("current_stock", 0) * p.get("unit_cost", 0) for p in supplier_products)
                
                # Get performance metrics (would come from historical data)
                on_time_delivery = supplier.get("on_time_delivery_rate", 85.0)
                quality_score = supplier.get("quality_rating", 4.0) * 20  # Convert to percentage
                cost_competitiveness = supplier.get("cost_competitiveness", 75.0)
                
                # Calculate relationship score based on various factors
                relationship_score = (on_time_delivery + quality_score + cost_competitiveness) / 3
                
                # Determine risk level
                risk_level = "low"
                if on_time_delivery < 80 or quality_score < 70:
                    risk_level = "high"
                elif on_time_delivery < 90 or quality_score < 80:
                    risk_level = "medium"
                
                performance = SupplierPerformance(
                    supplier_name=supplier_name,
                    on_time_delivery_rate=on_time_delivery,
                    quality_score=quality_score,
                    cost_competitiveness=cost_competitiveness,
                    relationship_score=relationship_score,
                    total_value=total_value,
                    risk_level=risk_level
                )
                
                supplier_performances.append(performance)
            
            return sorted(supplier_performances, key=lambda s: s.relationship_score, reverse=True)
            
        except Exception as e:
            logger.error("Failed to analyze supplier performance", error=str(e))
            return []
    
    async def generate_ai_insights(self, time_period: int = 30) -> List[AnalyticsInsight]:
        """Generate AI-powered business insights"""
        try:
            insights = []
            
            # Get current data for analysis
            current_data = await self._gather_analytics_data(time_period)
            
            # Analyze inventory levels
            insights.extend(await self._analyze_inventory_level_insights(current_data))
            
            # Analyze demand patterns
            insights.extend(await self._analyze_demand_pattern_insights(current_data))
            
            # Analyze supplier performance
            insights.extend(await self._analyze_supplier_insights(current_data))
            
            # Analyze seasonal trends
            insights.extend(await self._analyze_seasonal_insights(current_data))
            
            # Sort by impact and confidence
            insights.sort(key=lambda i: (i.impact == "high", i.confidence_score), reverse=True)
            
            return insights[:10]  # Return top 10 insights
            
        except Exception as e:
            logger.error("Failed to generate AI insights", error=str(e))
            return []
    
    async def analyze_inventory_trends(self, time_period: int = 30) -> Dict[str, Any]:
        """Analyze inventory trends and patterns"""
        try:
            # Get historical data
            historical_data = await self._get_historical_trend_data(time_period)
            
            trends = {
                "stock_level_trend": self._analyze_stock_level_trend(historical_data),
                "demand_trend": self._analyze_demand_trend(historical_data),
                "cost_trend": self._analyze_cost_trend(historical_data),
                "seasonality": self._analyze_seasonality(historical_data),
                "velocity_changes": self._analyze_velocity_changes(historical_data)
            }
            
            return trends
            
        except Exception as e:
            logger.error("Failed to analyze inventory trends", error=str(e))
            return {}
    
    async def calculate_inventory_health_score(self) -> Dict[str, Any]:
        """Calculate overall inventory health score"""
        try:
            # Get various health metrics
            stock_level_score = await self._calculate_stock_level_health()
            demand_fulfillment_score = await self._calculate_demand_fulfillment_health()
            cost_efficiency_score = await self._calculate_cost_efficiency_health()
            turnover_score = await self._calculate_turnover_health()
            forecast_score = await self._calculate_forecast_health()
            
            # Weighted average
            weights = {
                "stock_level": 0.25,
                "demand_fulfillment": 0.30,
                "cost_efficiency": 0.20,
                "turnover": 0.15,
                "forecast": 0.10
            }
            
            overall_score = (
                stock_level_score * weights["stock_level"] +
                demand_fulfillment_score * weights["demand_fulfillment"] +
                cost_efficiency_score * weights["cost_efficiency"] +
                turnover_score * weights["turnover"] +
                forecast_score * weights["forecast"]
            )
            
            # Determine health status
            if overall_score >= 85:
                status = "excellent"
            elif overall_score >= 70:
                status = "good"
            elif overall_score >= 55:
                status = "fair"
            else:
                status = "poor"
            
            return {
                "overall_score": round(overall_score, 1),
                "status": status,
                "components": {
                    "stock_level": round(stock_level_score, 1),
                    "demand_fulfillment": round(demand_fulfillment_score, 1),
                    "cost_efficiency": round(cost_efficiency_score, 1),
                    "turnover": round(turnover_score, 1),
                    "forecast": round(forecast_score, 1)
                },
                "recommendations": self._generate_health_recommendations(overall_score, {
                    "stock_level": stock_level_score,
                    "demand_fulfillment": demand_fulfillment_score,
                    "cost_efficiency": cost_efficiency_score,
                    "turnover": turnover_score,
                    "forecast": forecast_score
                })
            }
            
        except Exception as e:
            logger.error("Failed to calculate inventory health score", error=str(e))
            return {"overall_score": 0, "status": "unknown", "error": str(e)}
    
    # Helper Methods
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.analytics_cache:
            return False
        
        cached_data = self.analytics_cache[cache_key]
        cache_time = datetime.fromisoformat(cached_data.get("cached_at", "2000-01-01T00:00:00"))
        
        return datetime.utcnow() - cache_time < self.cache_duration
    
    def _cache_result(self, cache_key: str, data: Dict[str, Any]):
        """Cache analysis result"""
        data["cached_at"] = datetime.utcnow().isoformat()
        self.analytics_cache[cache_key] = data
    
    def _calculate_trend(self, current: float, previous: float) -> str:
        """Calculate trend direction"""
        if abs(current - previous) < 0.01:  # Consider negligible changes as stable
            return "stable"
        elif current > previous:
            return "up"
        else:
            return "down"
    
    def _calculate_change_percentage(self, current: float, previous: float) -> float:
        """Calculate percentage change"""
        if previous == 0:
            return 0.0
        return ((current - previous) / previous) * 100
    
    async def _get_all_products(self) -> List[Dict]:
        """Get all products from database"""
        db = get_db()
        return list(db.products.find())
    
    async def _get_low_stock_items(self) -> List[Dict]:
        """Get products with low stock"""
        db = get_db()
        return list(db.products.find({"current_stock": {"$lte": "$reorder_point"}}))
    
    async def _get_out_of_stock_items(self) -> List[Dict]:
        """Get products that are out of stock"""
        db = get_db()
        return list(db.products.find({"current_stock": 0}))
    
    async def _get_overstock_items(self) -> List[Dict]:
        """Get products with excess stock"""
        db = get_db()
        pipeline = [
            {
                "$addFields": {
                    "overstock_ratio": {"$divide": ["$current_stock", "$max_stock"]}
                }
            },
            {
                "$match": {"overstock_ratio": {"$gt": 1.5}}
            }
        ]
        return list(db.products.aggregate(pipeline))
    
    # Implement additional helper methods for calculations...
    # (Due to length, I'll provide key methods - you can expand based on needs)
    
    async def _calculate_inventory_turnover(self, days: int) -> Dict[str, float]:
        """Calculate inventory turnover rate"""
        # Simplified calculation - would use actual COGS and average inventory
        return {"current": 5.2, "previous": 4.8}
    
    async def _calculate_stockout_rate(self, days: int) -> Dict[str, float]:
        """Calculate stock-out rate"""
        # Would calculate based on actual stockout events
        return {"current": 3.5, "previous": 4.2}
    
    async def _calculate_carrying_cost(self, days: int) -> Dict[str, float]:
        """Calculate carrying cost"""
        # Would calculate based on storage, insurance, taxes, etc.
        return {"current": 15000.0, "previous": 14500.0}
    
    async def _calculate_forecast_accuracy(self, days: int) -> Dict[str, float]:
        """Calculate forecast accuracy"""
        # Would compare forecasts vs actual demand
        return {"current": 82.5, "previous": 79.1}
    
    async def _calculate_fill_rate(self, days: int) -> Dict[str, float]:
        """Calculate order fill rate"""
        # Would calculate based on fulfilled vs total orders
        return {"current": 94.2, "previous": 92.8}
    
    def _calculate_product_risk_score(self, inventory: Dict, sales: Dict) -> float:
        """Calculate risk score for a product"""
        # Simplified risk calculation based on multiple factors
        base_risk = 30.0
        
        # Stock level risk
        current_stock = inventory.get("current_stock", 0)
        reorder_point = inventory.get("reorder_point", 10)
        if current_stock <= reorder_point:
            base_risk += 40.0
        
        # Demand volatility risk
        volatility = sales.get("demand_volatility", 1.0)
        if volatility > 2.0:
            base_risk += 20.0
        
        # Supplier risk
        supplier_rating = inventory.get("supplier_rating", 5.0)
        if supplier_rating < 3.0:
            base_risk += 30.0
        
        return min(base_risk, 100.0)
    
    async def _get_product_forecast_accuracy(self, product_id: str) -> float:
        """Get forecast accuracy for a specific product"""
        # Would calculate based on historical forecast vs actual
        return 78.5  # Placeholder
    
    async def _gather_analytics_data(self, time_period: int) -> Dict[str, Any]:
        """Gather all necessary data for AI insights"""
        return {
            "products": await self._get_all_products(),
            "sales_data": await self._get_product_sales_data(time_period),
            "suppliers": await self._get_supplier_data(),
            "alerts": await self._get_recent_alerts(time_period)
        }
    
    async def _analyze_inventory_level_insights(self, data: Dict) -> List[AnalyticsInsight]:
        """Generate insights about inventory levels"""
        insights = []
        
        # Example insight about low stock items
        low_stock_count = len([p for p in data["products"] if p.get("current_stock", 0) <= p.get("reorder_point", 10)])
        
        if low_stock_count > 10:
            insights.append(AnalyticsInsight(
                insight_id=f"low_stock_alert_{datetime.utcnow().strftime('%Y%m%d')}",
                category="inventory_levels",
                title="High Number of Low Stock Items",
                description=f"You have {low_stock_count} items below reorder point, indicating potential supply chain issues.",
                impact="high",
                actionable=True,
                recommendation="Review reorder points and supplier lead times. Consider emergency procurement for critical items.",
                confidence_score=0.95,
                supporting_data={"low_stock_count": low_stock_count}
            ))
        
        return insights
    
    # Additional analysis methods would be implemented here...
    async def _analyze_demand_pattern_insights(self, data: Dict) -> List[AnalyticsInsight]:
        return []
    
    async def _analyze_supplier_insights(self, data: Dict) -> List[AnalyticsInsight]:
        return []
    
    async def _analyze_seasonal_insights(self, data: Dict) -> List[AnalyticsInsight]:
        return []
    
    # Health score calculation methods
    async def _calculate_stock_level_health(self) -> float:
        return 85.0  # Placeholder
    
    async def _calculate_demand_fulfillment_health(self) -> float:
        return 90.0  # Placeholder
    
    async def _calculate_cost_efficiency_health(self) -> float:
        return 75.0  # Placeholder
    
    async def _calculate_turnover_health(self) -> float:
        return 80.0  # Placeholder
    
    async def _calculate_forecast_health(self) -> float:
        return 82.0  # Placeholder
    
    def _generate_health_recommendations(self, overall_score: float, components: Dict) -> List[str]:
        """Generate recommendations based on health scores"""
        recommendations = []
        
        if overall_score < 70:
            recommendations.append("Consider reviewing inventory management processes")
        
        if components.get("demand_fulfillment", 0) < 70:
            recommendations.append("Focus on improving demand fulfillment rates")
        
        if components.get("cost_efficiency", 0) < 70:
            recommendations.append("Optimize inventory costs and carrying expenses")
        
        return recommendations
    
    # Placeholder methods for data gathering
    async def _get_product_sales_data(self, days_back: int) -> Dict[str, Dict]:
        return {}
    
    async def _get_current_inventory_data(self) -> Dict[str, Dict]:
        return {}
    
    async def _get_supplier_data(self) -> List[Dict]:
        return []
    
    async def _get_recent_alerts(self, days: int) -> List[Dict]:
        return []
    
    async def _get_historical_trend_data(self, days: int) -> Dict:
        return {}
    
    def _analyze_stock_level_trend(self, data: Dict) -> Dict:
        return {"trend": "stable", "change": 0.5}
    
    def _analyze_demand_trend(self, data: Dict) -> Dict:
        return {"trend": "increasing", "change": 5.2}
    
    def _analyze_cost_trend(self, data: Dict) -> Dict:
        return {"trend": "stable", "change": 1.1}
    
    def _analyze_seasonality(self, data: Dict) -> Dict:
        return {"seasonal_pattern": "moderate", "peak_months": ["November", "December"]}
    
    def _analyze_velocity_changes(self, data: Dict) -> Dict:
        return {"fast_movers": 5, "slow_movers": 12}

# Global instance
advanced_analytics_service = AdvancedAnalyticsService() 
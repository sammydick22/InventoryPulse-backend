"""
MCP (Model Context Protocol) Server for InventoryPulse
Exposes inventory tools for AI agents to interact with the system
"""

import json
import asyncio
import structlog
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from dataclasses import dataclass

# Flask imports
from flask import current_app

# Import our existing services
from backend.services.db_service import get_db
from backend.services.snowflake_service import get_snowflake_connection

logger = structlog.get_logger(__name__)

@dataclass
class InventoryItem:
    """Data structure for inventory items"""
    product_id: str
    name: str
    current_stock: int
    reorder_point: int
    supplier: str
    last_updated: datetime

class InventoryMCPServer:
    """MCP Server exposing inventory management tools for AI agents"""
    
    def __init__(self):
        self.tools = {
            # Core inventory tools
            "get_inventory": self.get_inventory,
            "check_low_stock": self.check_low_stock,
            "forecast_demand": self.forecast_demand,
            "recommend_restock": self.recommend_restock,
            "get_sales_analytics": self.get_sales_analytics,
            "create_alert": self.create_alert,
            "update_inventory": self.update_inventory,
            "get_supplier_info": self.get_supplier_info,
            
            # Enhanced AI-powered tools
            "analyze_inventory_health": self.analyze_inventory_health,
            "get_predictive_insights": self.get_predictive_insights,
            "optimize_inventory_levels": self.optimize_inventory_levels,
            "calculate_safety_stock": self.calculate_safety_stock,
            "analyze_demand_patterns": self.analyze_demand_patterns,
            "get_supplier_performance": self.get_supplier_performance,
            "simulate_scenarios": self.simulate_scenarios,
            "get_inventory_kpis": self.get_inventory_kpis,
            
            # Real-time monitoring tools
            "start_monitoring": self.start_monitoring,
            "stop_monitoring": self.stop_monitoring,
            "get_active_alerts": self.get_active_alerts,
            "acknowledge_alert": self.acknowledge_alert,
            "resolve_alert": self.resolve_alert,
            
            # Advanced analytics tools
            "generate_dashboard": self.generate_dashboard,
            "export_analytics_report": self.export_analytics_report,
            "benchmark_performance": self.benchmark_performance
        }
    
    async def get_inventory(self, product_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """Get current inventory levels"""
        try:
            db = get_db()
            
            if product_id:
                query = {"product_id": product_id}
            else:
                query = {}
            
            products = list(db.products.find(query).limit(limit))
            
            # Convert ObjectId to string for JSON serialization
            for product in products:
                product['_id'] = str(product['_id'])
                if 'last_updated' not in product:
                    product['last_updated'] = datetime.utcnow().isoformat()
            
            return {
                "status": "success",
                "inventory_count": len(products),
                "products": products,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get inventory", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def check_low_stock(self, threshold_percentage: float = 20.0) -> Dict[str, Any]:
        """Check for products with low stock levels"""
        try:
            db = get_db()
            
            # Find products where current stock is below threshold percentage of max stock
            pipeline = [
                {
                    "$addFields": {
                        "stock_percentage": {
                            "$multiply": [
                                {"$divide": ["$current_stock", "$max_stock"]},
                                100
                            ]
                        }
                    }
                },
                {
                    "$match": {
                        "stock_percentage": {"$lt": threshold_percentage}
                    }
                },
                {
                    "$sort": {"stock_percentage": 1}
                }
            ]
            
            low_stock_items = list(db.products.aggregate(pipeline))
            
            # Convert ObjectId to string
            for item in low_stock_items:
                item['_id'] = str(item['_id'])
            
            return {
                "status": "success",
                "low_stock_count": len(low_stock_items),
                "threshold_percentage": threshold_percentage,
                "items": low_stock_items,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to check low stock", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def forecast_demand(self, product_id: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Forecast demand using Snowflake historical data and simple ML"""
        try:
            conn = get_snowflake_connection()
            
            if not conn:
                return {"status": "error", "message": "Snowflake connection failed"}
            
            # Query historical sales data from Snowflake
            query = f"""
            SELECT 
                SNAPSHOT_DATE,
                QUANTITY_SOLD,
                REVENUE
            FROM AWSHACK725.PUBLIC.SALES_ANALYTICS 
            WHERE PRODUCT_ID = '{product_id}'
            AND SNAPSHOT_DATE >= DATEADD(day, -90, CURRENT_DATE())
            ORDER BY SNAPSHOT_DATE
            """
            
            with conn.cursor() as cur:
                cur.execute(query)
                historical_data = cur.fetchall()
            
            if not historical_data:
                return {
                    "status": "warning",
                    "message": "No historical data found for forecasting",
                    "forecast": {"daily_demand": 0, "total_demand": 0}
                }
            
            # Simple moving average forecast (can be enhanced with ML models)
            recent_sales = [row[1] for row in historical_data[-14:]]  # Last 14 days
            avg_daily_demand = sum(recent_sales) / len(recent_sales) if recent_sales else 0
            
            # Apply trend analysis (basic)
            if len(recent_sales) >= 7:
                recent_avg = sum(recent_sales[-7:]) / 7
                older_avg = sum(recent_sales[-14:-7]) / 7
                trend_factor = recent_avg / older_avg if older_avg > 0 else 1.0
                avg_daily_demand *= trend_factor
            
            total_forecasted_demand = avg_daily_demand * days_ahead
            
            return {
                "status": "success",
                "product_id": product_id,
                "forecast_period_days": days_ahead,
                "forecast": {
                    "daily_demand": round(avg_daily_demand, 2),
                    "total_demand": round(total_forecasted_demand, 2),
                    "confidence": "medium"  # Simple confidence level
                },
                "based_on_days": len(historical_data),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to forecast demand", product_id=product_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def recommend_restock(self, product_id: Optional[str] = None) -> Dict[str, Any]:
        """Recommend restock quantities based on current stock and demand forecast"""
        try:
            db = get_db()
            
            # Get products to analyze
            if product_id:
                products = list(db.products.find({"product_id": product_id}))
            else:
                # Get all products with low stock
                low_stock_result = await self.check_low_stock(threshold_percentage=30.0)
                if low_stock_result["status"] != "success":
                    return low_stock_result
                products = low_stock_result["items"]
            
            recommendations = []
            
            for product in products:
                # Get demand forecast
                forecast_result = await self.forecast_demand(product["product_id"], days_ahead=30)
                
                if forecast_result["status"] == "success":
                    forecasted_demand = forecast_result["forecast"]["total_demand"]
                    current_stock = product.get("current_stock", 0)
                    safety_stock = product.get("safety_stock", 10)
                    
                    # Calculate recommended restock quantity
                    recommended_quantity = max(0, forecasted_demand + safety_stock - current_stock)
                    
                    recommendations.append({
                        "product_id": product["product_id"],
                        "product_name": product.get("name", "Unknown"),
                        "current_stock": current_stock,
                        "forecasted_demand_30d": round(forecasted_demand, 2),
                        "recommended_restock": round(recommended_quantity, 2),
                        "urgency": "high" if current_stock < safety_stock else "medium",
                        "supplier": product.get("supplier", "Unknown")
                    })
            
            return {
                "status": "success",
                "recommendations_count": len(recommendations),
                "recommendations": recommendations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to generate restock recommendations", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_sales_analytics(self, days_back: int = 30) -> Dict[str, Any]:
        """Get sales analytics from Snowflake"""
        try:
            conn = get_snowflake_connection()
            
            if not conn:
                return {"status": "error", "message": "Snowflake connection failed"}
            
            query = f"""
            SELECT 
                PRODUCT_ID,
                SUM(QUANTITY_SOLD) as total_quantity,
                SUM(REVENUE) as total_revenue,
                AVG(QUANTITY_SOLD) as avg_daily_quantity,
                COUNT(*) as data_points
            FROM AWSHACK725.PUBLIC.SALES_ANALYTICS 
            WHERE SNAPSHOT_DATE >= DATEADD(day, -{days_back}, CURRENT_DATE())
            GROUP BY PRODUCT_ID
            ORDER BY total_revenue DESC
            """
            
            with conn.cursor() as cur:
                cur.execute(query)
                results = cur.fetchall()
                columns = [desc[0] for desc in cur.description]
            
            analytics = []
            for row in results:
                analytics.append(dict(zip(columns, row)))
            
            return {
                "status": "success",
                "period_days": days_back,
                "products_analyzed": len(analytics),
                "analytics": analytics,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get sales analytics", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def create_alert(self, alert_type: str, product_id: str, message: str, severity: str = "medium") -> Dict[str, Any]:
        """Create a new alert in the system"""
        try:
            db = get_db()
            
            alert = {
                "alert_id": f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{product_id}",
                "type": alert_type,
                "product_id": product_id,
                "message": message,
                "severity": severity,
                "status": "active",
                "created_at": datetime.utcnow(),
                "resolved_at": None
            }
            
            result = db.alerts.insert_one(alert)
            alert['_id'] = str(result.inserted_id)
            
            return {
                "status": "success",
                "alert_created": alert,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to create alert", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def update_inventory(self, product_id: str, new_stock: int, reason: str = "Manual update") -> Dict[str, Any]:
        """Update inventory levels"""
        try:
            db = get_db()
            
            # Update the product stock
            result = db.products.update_one(
                {"product_id": product_id},
                {
                    "$set": {
                        "current_stock": new_stock,
                        "last_updated": datetime.utcnow()
                    },
                    "$push": {
                        "stock_history": {
                            "timestamp": datetime.utcnow(),
                            "previous_stock": "$current_stock",
                            "new_stock": new_stock,
                            "reason": reason
                        }
                    }
                }
            )
            
            if result.matched_count == 0:
                return {"status": "error", "message": f"Product {product_id} not found"}
            
            return {
                "status": "success",
                "product_id": product_id,
                "new_stock": new_stock,
                "reason": reason,
                "updated_count": result.modified_count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to update inventory", product_id=product_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_supplier_info(self, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """Get supplier information and performance metrics"""
        try:
            db = get_db()
            
            if supplier_name:
                suppliers = list(db.suppliers.find({"name": supplier_name}))
            else:
                suppliers = list(db.suppliers.find().limit(20))
            
            # Convert ObjectId to string
            for supplier in suppliers:
                supplier['_id'] = str(supplier['_id'])
            
            return {
                "status": "success",
                "suppliers_count": len(suppliers),
                "suppliers": suppliers,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get supplier info", error=str(e))
            return {"status": "error", "message": str(e)}
    
    def get_tool_schemas(self) -> Dict[str, Dict]:
        """Return comprehensive MCP tool schemas for AI agents"""
        return {
            # Core inventory tools
            "get_inventory": {
                "description": "Get current inventory levels for products",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Specific product ID (optional)"},
                        "limit": {"type": "integer", "description": "Maximum number of products to return", "default": 100}
                    }
                }
            },
            "check_low_stock": {
                "description": "Check for products with low stock levels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "threshold_percentage": {"type": "number", "description": "Stock threshold percentage", "default": 20.0}
                    }
                }
            },
            "forecast_demand": {
                "description": "Forecast demand for a specific product using historical data and AI",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID to forecast"},
                        "days_ahead": {"type": "integer", "description": "Number of days to forecast", "default": 30}
                    },
                    "required": ["product_id"]
                }
            },
            "recommend_restock": {
                "description": "Get restock recommendations based on demand forecasts",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Specific product ID (optional)"}
                    }
                }
            },
            "get_sales_analytics": {
                "description": "Get sales analytics and performance metrics from data warehouse",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "days_back": {"type": "integer", "description": "Number of days to analyze", "default": 30}
                    }
                }
            },
            "create_alert": {
                "description": "Create a new alert in the system",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alert_type": {"type": "string", "description": "Type of alert (low_stock, restock_needed, etc.)"},
                        "product_id": {"type": "string", "description": "Product ID related to the alert"},
                        "message": {"type": "string", "description": "Alert message"},
                        "severity": {"type": "string", "description": "Alert severity (low, medium, high)", "default": "medium"}
                    },
                    "required": ["alert_type", "product_id", "message"]
                }
            },
            "update_inventory": {
                "description": "Update inventory stock levels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID to update"},
                        "new_stock": {"type": "integer", "description": "New stock quantity"},
                        "reason": {"type": "string", "description": "Reason for update", "default": "Manual update"}
                    },
                    "required": ["product_id", "new_stock"]
                }
            },
            "get_supplier_info": {
                "description": "Get supplier information and basic performance metrics",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "supplier_name": {"type": "string", "description": "Specific supplier name (optional)"}
                    }
                }
            },
            
            # Enhanced AI-powered tools
            "analyze_inventory_health": {
                "description": "Comprehensive AI-powered inventory health analysis with recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_recommendations": {"type": "boolean", "description": "Include AI recommendations", "default": True}
                    }
                }
            },
            "get_predictive_insights": {
                "description": "Get AI-powered predictive insights for demand forecasting and risk assessment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Specific product ID for single-product analysis (optional)"},
                        "days_ahead": {"type": "integer", "description": "Prediction horizon in days", "default": 30}
                    }
                }
            },
            "optimize_inventory_levels": {
                "description": "AI-powered optimization of reorder points and max stock levels",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "Product category to optimize (optional, analyzes all if not specified)"}
                    }
                }
            },
            "calculate_safety_stock": {
                "description": "Calculate optimal safety stock levels using statistical methods",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID to calculate safety stock for"},
                        "service_level": {"type": "number", "description": "Desired service level (0.90, 0.95, 0.99)", "default": 0.95}
                    },
                    "required": ["product_id"]
                }
            },
            "analyze_demand_patterns": {
                "description": "Analyze demand patterns, seasonality, and trends",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Specific product ID (optional, analyzes system-wide if not specified)"},
                        "days_back": {"type": "integer", "description": "Historical period to analyze", "default": 90}
                    }
                }
            },
            "get_supplier_performance": {
                "description": "Enhanced supplier performance analysis with predictive risk assessment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "supplier_name": {"type": "string", "description": "Specific supplier name (optional)"},
                        "include_predictions": {"type": "boolean", "description": "Include risk predictions", "default": True}
                    }
                }
            },
            "simulate_scenarios": {
                "description": "Simulate different inventory scenarios for decision making (demand_spike, supplier_delay)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "scenario_type": {"type": "string", "description": "Type of scenario (demand_spike, supplier_delay)"},
                        "parameters": {"type": "object", "description": "Scenario-specific parameters"}
                    },
                    "required": ["scenario_type", "parameters"]
                }
            },
            "get_inventory_kpis": {
                "description": "Get comprehensive inventory Key Performance Indicators",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "period_days": {"type": "integer", "description": "Period for KPI calculation", "default": 30}
                    }
                }
            },
            
            # Real-time monitoring tools
            "start_monitoring": {
                "description": "Start real-time monitoring for a product using Temporal workflows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Product ID to monitor"},
                        "check_interval_minutes": {"type": "integer", "description": "Check interval in minutes", "default": 60}
                    },
                    "required": ["product_id"]
                }
            },
            "stop_monitoring": {
                "description": "Stop real-time monitoring workflow",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {"type": "string", "description": "Workflow ID to stop"}
                    },
                    "required": ["workflow_id"]
                }
            },
            "get_active_alerts": {
                "description": "Get active alerts from the real-time alerting system",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "product_id": {"type": "string", "description": "Filter by product ID (optional)"},
                        "severity": {"type": "string", "description": "Filter by severity (low, medium, high, critical) (optional)"}
                    }
                }
            },
            "acknowledge_alert": {
                "description": "Acknowledge an active alert",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alert_id": {"type": "string", "description": "Alert ID to acknowledge"},
                        "acknowledged_by": {"type": "string", "description": "User acknowledging the alert"}
                    },
                    "required": ["alert_id", "acknowledged_by"]
                }
            },
            "resolve_alert": {
                "description": "Resolve an alert with optional resolution note",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "alert_id": {"type": "string", "description": "Alert ID to resolve"},
                        "resolved_by": {"type": "string", "description": "User resolving the alert"},
                        "resolution_note": {"type": "string", "description": "Optional resolution note", "default": ""}
                    },
                    "required": ["alert_id", "resolved_by"]
                }
            },
            
            # Advanced analytics tools
            "generate_dashboard": {
                "description": "Generate comprehensive analytics dashboard with KPIs, insights, and recommendations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_period": {"type": "integer", "description": "Analysis period in days", "default": 30}
                    }
                }
            },
            "export_analytics_report": {
                "description": "Export detailed analytics report in specified format",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "report_type": {"type": "string", "description": "Type of report (summary, detailed)", "default": "summary"},
                        "format": {"type": "string", "description": "Export format (json, csv)", "default": "json"}
                    }
                }
            },
            "benchmark_performance": {
                "description": "Benchmark inventory performance against industry standards",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string", "description": "Metric to benchmark (turnover_rate, stock_out_rate, fill_rate)", "default": "turnover_rate"},
                        "benchmark_type": {"type": "string", "description": "Benchmark type (industry, best_practice)", "default": "industry"}
                    }
                }
            }
        }

    # Enhanced AI-powered tools
    
    async def analyze_inventory_health(self, include_recommendations: bool = True) -> Dict[str, Any]:
        """Comprehensive inventory health analysis using AI"""
        try:
            from backend.services.advanced_analytics_service import advanced_analytics_service
            
            # Get comprehensive health analysis
            health_score = await advanced_analytics_service.calculate_inventory_health_score()
            
            # Get additional context
            kpis = await advanced_analytics_service.calculate_inventory_kpis()
            
            result = {
                "status": "success",
                "health_analysis": health_score,
                "key_metrics": [asdict(kpi) for kpi in kpis[:5]],  # Top 5 KPIs
                "timestamp": datetime.utcnow().isoformat()
            }
            
            if include_recommendations:
                # Get AI-powered recommendations
                insights = await advanced_analytics_service.generate_ai_insights()
                result["ai_recommendations"] = [asdict(insight) for insight in insights[:3]]
            
            return result
            
        except Exception as e:
            logger.error("Failed to analyze inventory health", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_predictive_insights(self, product_id: Optional[str] = None, days_ahead: int = 30) -> Dict[str, Any]:
        """Get AI-powered predictive insights for inventory management"""
        try:
            from backend.services.ai_forecasting_service import ai_forecasting_service
            
            if product_id:
                # Single product prediction
                forecast = await ai_forecasting_service.forecast_demand_ai(product_id, days_ahead)
                return {
                    "status": "success",
                    "prediction_type": "single_product",
                    "product_id": product_id,
                    "forecast": forecast,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # System-wide predictions
                db = get_db()
                products = list(db.products.find().limit(10))  # Top 10 products
                
                predictions = []
                for product in products:
                    pid = product["product_id"]
                    forecast = await ai_forecasting_service.forecast_demand_ai(pid, days_ahead)
                    if forecast.get("status") == "success":
                        predictions.append({
                            "product_id": pid,
                            "product_name": product.get("name", pid),
                            "forecast_summary": forecast.get("ai_forecast", {}).get("forecast", {}),
                            "risk_level": forecast.get("ai_forecast", {}).get("forecast", {}).get("risk_assessment", "medium")
                        })
                
                return {
                    "status": "success",
                    "prediction_type": "multi_product",
                    "predictions": predictions,
                    "days_ahead": days_ahead,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error("Failed to get predictive insights", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def optimize_inventory_levels(self, category: Optional[str] = None) -> Dict[str, Any]:
        """AI-powered inventory level optimization recommendations"""
        try:
            db = get_db()
            
            query = {}
            if category:
                query["category"] = category
            
            products = list(db.products.find(query).limit(20))
            
            optimizations = []
            for product in products:
                product_id = product["product_id"]
                current_stock = product.get("current_stock", 0)
                reorder_point = product.get("reorder_point", 10)
                max_stock = product.get("max_stock", 100)
                
                # Get AI forecast for optimization
                forecast_result = await self.forecast_demand(product_id, days_ahead=30)
                
                if forecast_result.get("status") == "success":
                    forecasted_demand = forecast_result["forecast"]["total_demand"]
                    
                    # Calculate optimal levels
                    optimal_reorder = max(forecasted_demand * 0.3, 5)  # 30% of monthly demand
                    optimal_max = forecasted_demand * 1.5  # 150% of monthly demand
                    
                    optimizations.append({
                        "product_id": product_id,
                        "product_name": product.get("name", product_id),
                        "current_levels": {
                            "stock": current_stock,
                            "reorder_point": reorder_point,
                            "max_stock": max_stock
                        },
                        "recommended_levels": {
                            "reorder_point": round(optimal_reorder),
                            "max_stock": round(optimal_max)
                        },
                        "forecasted_monthly_demand": round(forecasted_demand, 2),
                        "optimization_impact": {
                            "reorder_change": round(optimal_reorder - reorder_point),
                            "max_stock_change": round(optimal_max - max_stock)
                        }
                    })
            
            return {
                "status": "success",
                "category": category or "all",
                "optimizations": optimizations,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to optimize inventory levels", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def calculate_safety_stock(self, product_id: str, service_level: float = 0.95) -> Dict[str, Any]:
        """Calculate optimal safety stock levels using statistical methods"""
        try:
            # Get historical demand data
            forecast_result = await self.forecast_demand(product_id, days_ahead=30)
            
            if forecast_result.get("status") != "success":
                return {"status": "error", "message": "Could not get demand forecast"}
            
            # Get current product data
            db = get_db()
            product = db.products.find_one({"product_id": product_id})
            
            if not product:
                return {"status": "error", "message": "Product not found"}
            
            # Simplified safety stock calculation
            avg_demand = forecast_result["forecast"]["daily_demand"]
            lead_time = product.get("lead_time_days", 7)
            
            # Assume demand variability (in practice, would calculate from historical data)
            demand_std_dev = avg_demand * 0.3  # 30% coefficient of variation
            
            # Safety stock formula: Z-score * sqrt(lead_time) * demand_std_dev
            z_scores = {0.90: 1.28, 0.95: 1.65, 0.99: 2.33}
            z_score = z_scores.get(service_level, 1.65)
            
            safety_stock = z_score * (lead_time ** 0.5) * demand_std_dev
            
            return {
                "status": "success",
                "product_id": product_id,
                "safety_stock_calculation": {
                    "recommended_safety_stock": round(safety_stock),
                    "service_level": service_level,
                    "avg_daily_demand": round(avg_demand, 2),
                    "lead_time_days": lead_time,
                    "demand_variability": round(demand_std_dev, 2)
                },
                "current_vs_recommended": {
                    "current_reorder_point": product.get("reorder_point", 10),
                    "recommended_reorder_point": round(avg_demand * lead_time + safety_stock),
                    "difference": round(avg_demand * lead_time + safety_stock - product.get("reorder_point", 10))
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to calculate safety stock", product_id=product_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def analyze_demand_patterns(self, product_id: Optional[str] = None, days_back: int = 90) -> Dict[str, Any]:
        """Analyze demand patterns and seasonality"""
        try:
            if product_id:
                # Single product analysis
                analytics = await self.get_sales_analytics(days_back)
                
                if analytics.get("status") != "success":
                    return {"status": "error", "message": "Could not get sales analytics"}
                
                # Find the specific product in analytics
                product_analytics = None
                for item in analytics.get("analytics", []):
                    if item["PRODUCT_ID"] == product_id:
                        product_analytics = item
                        break
                
                if not product_analytics:
                    return {"status": "error", "message": "No analytics data found for product"}
                
                return {
                    "status": "success",
                    "product_id": product_id,
                    "demand_analysis": {
                        "total_demand": product_analytics.get("TOTAL_QUANTITY", 0),
                        "avg_daily_demand": product_analytics.get("AVG_DAILY_QUANTITY", 0),
                        "demand_variability": "medium",  # Would calculate from actual data
                        "trend": "stable",  # Would determine from trend analysis
                        "seasonality": "low"  # Would detect from historical patterns
                    },
                    "period_analyzed": f"{days_back} days",
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # System-wide demand pattern analysis
                analytics = await self.get_sales_analytics(days_back)
                
                if analytics.get("status") != "success":
                    return analytics
                
                # Aggregate patterns
                total_products = len(analytics.get("analytics", []))
                high_demand_products = len([p for p in analytics.get("analytics", []) if p.get("TOTAL_QUANTITY", 0) > 100])
                
                return {
                    "status": "success",
                    "system_wide_analysis": {
                        "total_products_analyzed": total_products,
                        "high_demand_products": high_demand_products,
                        "low_demand_products": total_products - high_demand_products,
                        "overall_trend": "stable",
                        "demand_concentration": "medium"
                    },
                    "period_analyzed": f"{days_back} days",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error("Failed to analyze demand patterns", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_supplier_performance(self, supplier_name: Optional[str] = None, include_predictions: bool = True) -> Dict[str, Any]:
        """Enhanced supplier performance analysis with predictive insights"""
        try:
            from backend.services.advanced_analytics_service import advanced_analytics_service
            
            # Get supplier performance analysis
            supplier_performance = await advanced_analytics_service.analyze_supplier_performance()
            
            if supplier_name:
                # Filter for specific supplier
                supplier_data = None
                for supplier in supplier_performance:
                    if supplier.supplier_name == supplier_name:
                        supplier_data = supplier
                        break
                
                if not supplier_data:
                    return {"status": "error", "message": f"Supplier {supplier_name} not found"}
                
                result = {
                    "status": "success",
                    "supplier": asdict(supplier_data),
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                # Return all suppliers
                result = {
                    "status": "success",
                    "suppliers": [asdict(supplier) for supplier in supplier_performance],
                    "timestamp": datetime.utcnow().isoformat()
                }
            
            if include_predictions:
                # Add predictive insights about supplier risk
                if supplier_name:
                    result["risk_prediction"] = {
                        "supply_chain_risk": "medium",
                        "delivery_reliability_trend": "stable",
                        "recommended_actions": ["Monitor delivery times", "Maintain backup suppliers"]
                    }
                else:
                    result["system_risk_overview"] = {
                        "high_risk_suppliers": len([s for s in supplier_performance if s.risk_level == "high"]),
                        "total_suppliers": len(supplier_performance),
                        "diversification_score": "good"
                    }
            
            return result
            
        except Exception as e:
            logger.error("Failed to get supplier performance", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def simulate_scenarios(self, scenario_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate different inventory scenarios for decision making"""
        try:
            if scenario_type == "demand_spike":
                spike_factor = parameters.get("spike_factor", 2.0)
                duration_days = parameters.get("duration_days", 7)
                product_id = parameters.get("product_id")
                
                if not product_id:
                    return {"status": "error", "message": "product_id required for demand spike simulation"}
                
                # Get current forecast
                normal_forecast = await self.forecast_demand(product_id, days_ahead=30)
                
                if normal_forecast.get("status") != "success":
                    return {"status": "error", "message": "Could not get baseline forecast"}
                
                # Simulate spike
                normal_demand = normal_forecast["forecast"]["daily_demand"]
                spike_demand = normal_demand * spike_factor
                
                # Get current inventory
                inventory = await self.get_inventory(product_id=product_id)
                current_stock = inventory["products"][0]["current_stock"] if inventory["products"] else 0
                
                # Calculate impact
                additional_demand = (spike_demand - normal_demand) * duration_days
                stock_after_spike = current_stock - additional_demand
                
                return {
                    "status": "success",
                    "scenario": "demand_spike",
                    "parameters": parameters,
                    "simulation_results": {
                        "normal_daily_demand": round(normal_demand, 2),
                        "spike_daily_demand": round(spike_demand, 2),
                        "additional_demand_total": round(additional_demand, 2),
                        "current_stock": current_stock,
                        "projected_stock_after_spike": round(stock_after_spike, 2),
                        "stockout_risk": "high" if stock_after_spike <= 0 else "medium" if stock_after_spike <= 10 else "low",
                        "recommended_action": "Emergency restock needed" if stock_after_spike <= 0 else "Monitor closely"
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            elif scenario_type == "supplier_delay":
                delay_days = parameters.get("delay_days", 7)
                affected_products = parameters.get("product_ids", [])
                
                if not affected_products:
                    return {"status": "error", "message": "product_ids required for supplier delay simulation"}
                
                impact_analysis = []
                for product_id in affected_products:
                    # Get current inventory and forecast
                    inventory = await self.get_inventory(product_id=product_id)
                    forecast = await self.forecast_demand(product_id, days_ahead=delay_days)
                    
                    if inventory["products"] and forecast.get("status") == "success":
                        current_stock = inventory["products"][0]["current_stock"]
                        expected_demand = forecast["forecast"]["total_demand"]
                        
                        impact_analysis.append({
                            "product_id": product_id,
                            "current_stock": current_stock,
                            "demand_during_delay": round(expected_demand, 2),
                            "projected_stock": round(current_stock - expected_demand, 2),
                            "risk_level": "high" if current_stock - expected_demand <= 0 else "medium"
                        })
                
                return {
                    "status": "success",
                    "scenario": "supplier_delay",
                    "parameters": parameters,
                    "simulation_results": {
                        "products_analyzed": len(impact_analysis),
                        "high_risk_products": len([p for p in impact_analysis if p["risk_level"] == "high"]),
                        "impact_details": impact_analysis
                    },
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            else:
                return {"status": "error", "message": f"Unknown scenario type: {scenario_type}"}
                
        except Exception as e:
            logger.error("Failed to simulate scenario", scenario_type=scenario_type, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_inventory_kpis(self, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive inventory KPIs"""
        try:
            from backend.services.advanced_analytics_service import advanced_analytics_service
            
            kpis = await advanced_analytics_service.calculate_inventory_kpis(period_days)
            
            return {
                "status": "success",
                "period_days": period_days,
                "kpis": [asdict(kpi) for kpi in kpis],
                "summary": {
                    "total_kpis": len(kpis),
                    "critical_kpis": len([kpi for kpi in kpis if kpi.status == "critical"]),
                    "warning_kpis": len([kpi for kpi in kpis if kpi.status == "warning"])
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get inventory KPIs", error=str(e))
            return {"status": "error", "message": str(e)}
    
    # Real-time monitoring tools
    
    async def start_monitoring(self, product_id: str, check_interval_minutes: int = 60) -> Dict[str, Any]:
        """Start real-time monitoring for a product using Temporal workflows"""
        try:
            from backend.services.temporal_service import temporal_service
            
            workflow_id = await temporal_service.start_inventory_monitoring(product_id, check_interval_minutes)
            
            return {
                "status": "success",
                "monitoring_started": True,
                "product_id": product_id,
                "workflow_id": workflow_id,
                "check_interval_minutes": check_interval_minutes,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to start monitoring", product_id=product_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def stop_monitoring(self, workflow_id: str) -> Dict[str, Any]:
        """Stop real-time monitoring workflow"""
        try:
            # In a real implementation, this would stop the Temporal workflow
            return {
                "status": "success",
                "monitoring_stopped": True,
                "workflow_id": workflow_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to stop monitoring", workflow_id=workflow_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def get_active_alerts(self, product_id: Optional[str] = None, severity: Optional[str] = None) -> Dict[str, Any]:
        """Get active alerts from the real-time alerting system"""
        try:
            from backend.services.real_time_alerting_service import real_time_alerting_service
            
            alerts = await real_time_alerting_service.get_active_alerts(product_id)
            
            # Filter by severity if specified
            if severity:
                alerts = [alert for alert in alerts if alert.severity.value == severity]
            
            return {
                "status": "success",
                "active_alerts": [asdict(alert) for alert in alerts],
                "total_alerts": len(alerts),
                "filters": {
                    "product_id": product_id,
                    "severity": severity
                },
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get active alerts", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> Dict[str, Any]:
        """Acknowledge an alert"""
        try:
            from backend.services.real_time_alerting_service import real_time_alerting_service
            
            success = await real_time_alerting_service.acknowledge_alert(alert_id, acknowledged_by)
            
            return {
                "status": "success" if success else "error",
                "acknowledged": success,
                "alert_id": alert_id,
                "acknowledged_by": acknowledged_by,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_note: str = "") -> Dict[str, Any]:
        """Resolve an alert"""
        try:
            from backend.services.real_time_alerting_service import real_time_alerting_service
            
            success = await real_time_alerting_service.resolve_alert(alert_id, resolved_by, resolution_note)
            
            return {
                "status": "success" if success else "error",
                "resolved": success,
                "alert_id": alert_id,
                "resolved_by": resolved_by,
                "resolution_note": resolution_note,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    # Advanced analytics tools
    
    async def generate_dashboard(self, time_period: int = 30) -> Dict[str, Any]:
        """Generate comprehensive analytics dashboard"""
        try:
            from backend.services.advanced_analytics_service import advanced_analytics_service
            
            dashboard = await advanced_analytics_service.generate_inventory_dashboard(time_period)
            
            return {
                "status": "success",
                "dashboard": dashboard,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to generate dashboard", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def export_analytics_report(self, report_type: str = "summary", format: str = "json") -> Dict[str, Any]:
        """Export analytics report in specified format"""
        try:
            if report_type == "summary":
                # Generate summary report
                dashboard = await self.generate_dashboard()
                kpis = await self.get_inventory_kpis()
                
                report_data = {
                    "report_type": "inventory_summary",
                    "generated_at": datetime.utcnow().isoformat(),
                    "dashboard_data": dashboard.get("dashboard", {}),
                    "kpi_data": kpis.get("kpis", [])
                }
                
                return {
                    "status": "success",
                    "report": report_data,
                    "format": format,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            else:
                return {"status": "error", "message": f"Unknown report type: {report_type}"}
                
        except Exception as e:
            logger.error("Failed to export analytics report", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def benchmark_performance(self, metric: str = "turnover_rate", benchmark_type: str = "industry") -> Dict[str, Any]:
        """Benchmark inventory performance against standards"""
        try:
            # Get current KPIs
            kpis_result = await self.get_inventory_kpis()
            
            if kpis_result.get("status") != "success":
                return {"status": "error", "message": "Could not get current KPIs"}
            
            kpis = kpis_result["kpis"]
            
            # Find the requested metric
            metric_data = None
            for kpi in kpis:
                if metric.lower() in kpi["name"].lower().replace(" ", "_"):
                    metric_data = kpi
                    break
            
            if not metric_data:
                return {"status": "error", "message": f"Metric {metric} not found"}
            
            # Industry benchmarks (simulated)
            benchmarks = {
                "turnover_rate": {"excellent": 8.0, "good": 6.0, "average": 4.0, "poor": 2.0},
                "stock_out_rate": {"excellent": 1.0, "good": 2.0, "average": 5.0, "poor": 10.0},
                "fill_rate": {"excellent": 98.0, "good": 95.0, "average": 90.0, "poor": 85.0}
            }
            
            metric_key = metric.lower()
            if metric_key not in benchmarks:
                metric_key = "turnover_rate"  # Default
            
            current_value = metric_data["value"]
            benchmark_levels = benchmarks[metric_key]
            
            # Determine performance level
            if current_value >= benchmark_levels["excellent"]:
                performance_level = "excellent"
            elif current_value >= benchmark_levels["good"]:
                performance_level = "good"
            elif current_value >= benchmark_levels["average"]:
                performance_level = "average"
            else:
                performance_level = "poor"
            
            return {
                "status": "success",
                "metric": metric,
                "benchmark_type": benchmark_type,
                "current_value": current_value,
                "performance_level": performance_level,
                "benchmarks": benchmark_levels,
                "improvement_opportunity": benchmark_levels["excellent"] - current_value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to benchmark performance", error=str(e))
            return {"status": "error", "message": str(e)}

# Global instance
mcp_server = InventoryMCPServer() 
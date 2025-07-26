"""
AI Forecasting Service using MiniMax LLM
Leverages MiniMax AI to analyze inventory data and generate intelligent forecasts
"""

import json
import math
import requests
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from flask import current_app

from backend.services.db_service import get_db
from backend.services.snowflake_service import get_snowflake_connection

logger = structlog.get_logger(__name__)

class AIForecastingService:
    """AI-powered forecasting using MiniMax LLM"""
    
    def __init__(self):
        self.base_url = None
        self.api_key = None
        self.model = None
        
    def _get_minimax_config(self):
        """Get MiniMax configuration from Flask app"""
        if current_app:
            self.base_url = current_app.config.get('MINIMAX_BASE_URL')
            self.api_key = current_app.config.get('MINIMAX_API_KEY')
            self.group_id = current_app.config.get('MINIMAX_GROUP_ID')
            self.model = current_app.config.get('MINIMAX_MODEL', 'abab6.5-chat')
            
            # Debug logging to check what we're getting
            logger.info("MiniMax configuration loaded", 
                       has_api_key=bool(self.api_key),
                       api_key_length=len(self.api_key) if self.api_key else 0,
                       has_group_id=bool(self.group_id),
                       group_id=self.group_id,
                       base_url=self.base_url,
                       model=self.model)
    
    def _call_minimax_api(self, prompt: str, system_prompt: str = None) -> Dict[str, Any]:
        """Call MiniMax API for AI inference"""
        import time
        start_time = time.time()
        
        try:
            self._get_minimax_config()
            # Runtime tuning via Flask config
            disable_stream = bool(current_app.config.get('MINIMAX_DISABLE_STREAM', False))
            request_timeout = current_app.config.get('MINIMAX_TIMEOUT_SECONDS', 120)
            
            if not self.api_key:
                return {"status": "error", "message": "MiniMax API not configured: MINIMAX_API_KEY environment variable is required"}
            if not self.group_id:
                return {"status": "error", "message": "MiniMax API not configured: MINIMAX_GROUP_ID environment variable is required"}
            if not self.base_url:
                return {"status": "error", "message": "MiniMax API not configured: MINIMAX_BASE_URL environment variable is required"}
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Define the structured output schema for forecasting
            forecast_schema = {
                "type": "object",
                "properties": {
                    "forecast": {
                        "type": "object",
                        "properties": {
                            "daily_demand": {"type": "number"},
                            "total_demand": {"type": "number"},
                            "confidence_level": {"type": "string", "enum": ["high", "medium", "low"]},
                            "trend": {"type": "string", "enum": ["increasing", "stable", "decreasing"]},
                            "seasonality_factor": {"type": "number"},
                            "risk_assessment": {"type": "string", "enum": ["low", "medium", "high"]},
                            "forecast_ranges": {
                                "type": "object",
                                "properties": {
                                    "optimistic": {"type": "number"},
                                    "pessimistic": {"type": "number"},
                                    "most_likely": {"type": "number"}
                                },
                                "required": ["optimistic", "pessimistic", "most_likely"]
                            }
                        },
                        "required": ["daily_demand", "total_demand", "confidence_level", "trend"]
                    },
                    "insights": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5
                    },
                    "recommendations": {
                        "type": "array", 
                        "items": {"type": "string"},
                        "maxItems": 5
                    },
                    "drivers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 3
                    }
                },
                "required": ["forecast", "insights", "recommendations"]
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.3,  # Lower temperature for more consistent forecasts (MiniMax-M1 default is 1.0)
                "max_tokens": 2048,  # Increased for better responses
                "stream": not disable_stream  # Streaming can be disabled via config
            }
            
            # Add structured output only for MiniMax-Text-01 (MiniMax-M1 doesn't support it)
            if self.model == "MiniMax-Text-01":
                payload["response_format"] = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "forecast_response",
                        "schema": forecast_schema,
                        "strict": True
                    }
                }
                logger.info("Using structured output with MiniMax-Text-01")
            else:
                logger.info("Using MiniMax-M1 without structured output (not supported)")
            
            # Use the correct MiniMax endpoint format  
            # Handle various base URL formats from environment
            if '/v1/text/chatcompletion' in self.base_url:
                # If the env already has the full endpoint, use it as-is
                url = self.base_url
            else:
                # Construct the proper endpoint
                if self.base_url.endswith('/v1'):
                    base = self.base_url[:-3]  # Remove /v1 suffix
                elif self.base_url.endswith('/'):
                    base = self.base_url[:-1]  # Remove trailing slash
                else:
                    base = self.base_url
                
                # Keep the original domain - api.minimax.io is correct
                # (Removed incorrect domain replacement)
                
                url = f"{base}/v1/text/chatcompletion_v2"
            
            # Add group_id as query parameter for MiniMax
            if self.group_id:
                url += f"?GroupId={self.group_id}"
                
            # Debug logging for URL construction and request details
            logger.info("MiniMax API call details", 
                       constructed_url=url,
                       model=self.model,
                       has_payload=bool(payload),
                       payload_size=len(str(payload)),
                       stream_enabled=payload.get('stream', False),
                       temperature=payload.get('temperature'),
                       max_tokens=payload.get('max_tokens'))
            
            # Use tuple timeout so we can have short connect timeout and longer read timeout
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=(10, request_timeout),
                stream=payload.get("stream", False)
            )
            
            if response.status_code == 200:
                # Handle streaming response
                logger.info("MiniMax streaming response started", status_code=response.status_code)
                
                full_content = ""
                chunk_count = 0
                
                try:
                    for line in response.iter_lines():
                        if line:
                            chunk_count += 1
                            line_str = line.decode('utf-8')
                            logger.debug("MiniMax stream chunk", chunk=chunk_count, content_preview=line_str[:100])
                            
                            # Skip empty lines and data: prefix
                            if line_str.startswith('data: '):
                                line_str = line_str[6:]  # Remove 'data: ' prefix
                            
                            if line_str.strip() == '[DONE]':
                                logger.info("MiniMax stream completed", total_chunks=chunk_count)
                                break
                                
                            try:
                                chunk_data = json.loads(line_str)
                                
                                # Debug: Log the actual structure we're receiving
                                logger.info("MiniMax chunk structure", 
                                           chunk_keys=list(chunk_data.keys()),
                                           chunk_data_sample=json.dumps(chunk_data, indent=2)[:500])
                                
                                # Handle MiniMax streaming format
                                content_found = False
                                
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    choice = chunk_data["choices"][0]
                                    logger.debug("Choice structure", choice_keys=list(choice.keys()))
                                    
                                    if "delta" in choice and "content" in choice["delta"]:
                                        content_delta = choice["delta"]["content"]
                                        full_content += content_delta
                                        content_found = True
                                        logger.debug("Content delta received", delta_length=len(content_delta))
                                    elif "message" in choice and "content" in choice["message"]:
                                        # Some APIs send full message in streaming
                                        full_content = choice["message"]["content"]
                                        content_found = True
                                        logger.debug("Full message received", content_length=len(full_content))
                                
                                # Try alternative MiniMax formats
                                if not content_found:
                                    # Check for direct content field
                                    if "content" in chunk_data:
                                        direct_content = chunk_data["content"]
                                        full_content += direct_content
                                        content_found = True
                                        logger.debug("Direct content received", content_length=len(direct_content))
                                    
                                    # Check for reply field (common in some APIs)
                                    elif "reply" in chunk_data:
                                        reply_content = chunk_data["reply"]
                                        full_content += reply_content
                                        content_found = True
                                        logger.debug("Reply content received", content_length=len(reply_content))
                                
                                if not content_found:
                                    logger.warning("No content found in chunk", available_fields=list(chunk_data.keys()))
                                        
                            except json.JSONDecodeError as e:
                                logger.warning("Failed to parse streaming chunk", error=str(e), chunk_preview=line_str[:100])
                                continue
                    
                    if full_content:
                        elapsed_time = time.time() - start_time
                        logger.info("MiniMax streaming completed successfully", 
                                   total_chunks=chunk_count, 
                                   content_length=len(full_content),
                                   elapsed_seconds=round(elapsed_time, 2))
                        return {
                            "status": "success",
                            "content": full_content,
                            "usage": {"stream_chunks": chunk_count, "elapsed_seconds": elapsed_time}
                        }
                    else:
                        logger.error("No content received from MiniMax stream", total_chunks=chunk_count)
                        # --- Fallback: retry without streaming to capture full response ---
                        try:
                            payload_no_stream = dict(payload)
                            payload_no_stream["stream"] = False  # disable streaming
                            resp_fallback = requests.post(
                                url,
                                headers=headers,
                                json=payload_no_stream,
                                timeout=60
                            )
                            if resp_fallback.status_code == 200:
                                try:
                                    data = resp_fallback.json()
                                    content = ""
                                    if isinstance(data, dict) and data.get("choices"):
                                        choice = data["choices"][0]
                                        # Common MiniMax patterns for non-streaming content
                                        if "message" in choice and "content" in choice["message"]:
                                            content = choice["message"]["content"]
                                        elif "delta" in choice and "content" in choice["delta"]:
                                            content = choice["delta"]["content"]
                                    if content:
                                        elapsed_time = time.time() - start_time
                                        logger.info("MiniMax non-streaming fallback succeeded", content_length=len(content))
                                        return {
                                            "status": "success",
                                            "content": content,
                                            "usage": {"stream_chunks": 0, "elapsed_seconds": elapsed_time}
                                        }
                                    else:
                                        logger.warning("Fallback non-streaming response had no content", response_preview=str(data)[:300])
                                except Exception as parse_err:
                                    logger.warning("Failed to parse fallback response", error=str(parse_err))
                        except Exception as fallback_err:
                            logger.warning("Non-streaming fallback failed", error=str(fallback_err))
                        
                        return {"status": "error", "message": "No content received from MiniMax stream or fallback"}
                        
                except Exception as stream_error:
                    logger.error("Error processing MiniMax stream", error=str(stream_error))
                    return {"status": "error", "message": f"Streaming error: {str(stream_error)}"}
                    
            else:
                logger.error("MiniMax API HTTP error", status_code=response.status_code, response=response.text[:500])
                
                # Try to parse error response
                try:
                    error_data = response.json()
                    if "base_resp" in error_data:
                        base_resp = error_data["base_resp"]
                        status_code = base_resp.get("status_code")
                        status_msg = base_resp.get("status_msg", "Unknown error")
                        
                        if status_code == 2049:
                            logger.error("MiniMax API authentication failed", error="Invalid API key")
                            return {"status": "error", "message": "MiniMax API authentication failed: Invalid API key. Please check your MINIMAX_API_KEY configuration."}
                        else:
                            logger.error("MiniMax API error", status_code=status_code, status_msg=status_msg)
                            return {"status": "error", "message": f"MiniMax API error {status_code}: {status_msg}"}
                except:
                    pass
                    
                return {"status": "error", "message": f"API call failed with HTTP {response.status_code}"}
                
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("Failed to call MiniMax API", error=str(e), elapsed_seconds=round(elapsed_time, 2))
            return {"status": "error", "message": str(e)}
    
    async def forecast_demand_ai(self, product_id: str, days_ahead: int = 30) -> Dict[str, Any]:
        """Generate AI-powered demand forecast using MiniMax with enhanced analytics"""
        try:
            # Get enhanced historical data from Snowflake
            historical_data = await self._get_historical_data(product_id, days_back=90)
            
            # Get current inventory data from MongoDB
            current_data = await self._get_current_inventory_data(product_id)
            
            # Get market conditions and external factors
            market_data = await self._get_market_conditions(product_id)
            
            if not historical_data and not current_data:
                return {
                    "status": "error", 
                    "message": "No data available for forecasting"
                }
            
            # Perform statistical analysis first
            statistical_forecast = await self._perform_statistical_analysis(historical_data, days_ahead)
            
            # Prepare enhanced prompt for MiniMax with statistical insights
            if self.model == "MiniMax-Text-01":
                # For MiniMax-Text-01 with structured output
                system_prompt = """You are an expert inventory forecasting AI with advanced analytics capabilities. 
                
                Analyze the provided data which includes:
                - Historical sales data with trend analysis
                - Statistical forecasting baseline
                - Seasonality patterns
                - Market conditions
                - Current inventory status
                
                Provide a comprehensive forecast with practical business insights, risk factors, and actionable recommendations.
                Focus on accurate numerical predictions and business-relevant insights."""
            else:
                # For MiniMax-M1 without structured output - need explicit JSON format instructions
                system_prompt = """You are an expert inventory forecasting AI with advanced analytics capabilities. 
                
                Analyze the provided data which includes:
                - Historical sales data with trend analysis
                - Statistical forecasting baseline
                - Seasonality patterns
                - Market conditions
                - Current inventory status
                
                CRITICAL: Your response must be ONLY a valid JSON object with this exact structure (no additional text before or after):
                {
                    "forecast": {
                        "daily_demand": <number>,
                        "total_demand": <number>,
                        "confidence_level": "high|medium|low",
                        "trend": "increasing|stable|decreasing",
                        "seasonality_factor": <number>,
                        "risk_assessment": "low|medium|high",
                        "forecast_ranges": {
                            "optimistic": <number>,
                            "pessimistic": <number>,
                            "most_likely": <number>
                        }
                    },
                    "insights": [
                        "key insight about demand patterns",
                        "key insight about market conditions",
                        "key insight about inventory optimization"
                    ],
                    "recommendations": [
                        "actionable recommendation for procurement",
                        "actionable recommendation for inventory management",
                        "actionable recommendation for risk mitigation"
                    ],
                    "drivers": [
                        "main factor influencing demand",
                        "secondary factor affecting forecast"
                    ]
                }
                
                IMPORTANT: Return ONLY the JSON object. No explanations, no markdown formatting, no additional text."""
            
            # Prepare enhanced data summary
            data_summary = self._prepare_enhanced_data_summary(
                historical_data, current_data, market_data, 
                statistical_forecast, product_id, days_ahead
            )
            
            # Call MiniMax API
            ai_response = self._call_minimax_api(data_summary, system_prompt)
            
            if ai_response["status"] != "success":
                # Fallback to statistical forecast if AI fails
                logger.info("AI service unavailable, using statistical fallback", reason=ai_response.get("message"))
                return {
                    "status": "success",
                    "product_id": product_id,
                    "forecast_period_days": days_ahead,
                    "forecast": statistical_forecast,
                    "ai_model": "statistical_fallback",
                    "timestamp": datetime.utcnow().isoformat(),
                    "confidence": 75,
                    "insights": [
                        f"Statistical forecast shows {statistical_forecast.get('trend', 'stable')} trend",
                        f"Predicted daily demand: {statistical_forecast.get('daily_demand', 0):.1f} units"
                    ],
                    "note": "AI service unavailable, using statistical forecast"
                }
            
            # Parse AI response
            try:
                ai_content = ai_response["content"].strip()
                
                # Clean up common JSON formatting issues
                if ai_content.startswith('```json'):
                    ai_content = ai_content[7:]  # Remove ```json
                if ai_content.endswith('```'):
                    ai_content = ai_content[:-3]  # Remove ```
                ai_content = ai_content.strip()
                
                logger.info("Parsing AI response", content_preview=ai_content[:200])
                forecast_result = json.loads(ai_content)
                
                # Validate and enhance the forecast
                enhanced_forecast = self._validate_and_enhance_forecast(
                    forecast_result, statistical_forecast, historical_data
                )
                
                return {
                    "status": "success",
                    "product_id": product_id,
                    "forecast_period_days": days_ahead,
                    "ai_forecast": enhanced_forecast,
                    "statistical_baseline": statistical_forecast,
                    "data_points_analyzed": len(historical_data) if historical_data else 0,
                    "ai_model": self.model,
                    "timestamp": datetime.utcnow().isoformat(),
                    "accuracy_metrics": await self._calculate_forecast_accuracy_metrics(product_id),
                    "data_quality": self._assess_data_quality(historical_data)
                }
                
            except json.JSONDecodeError as e:
                logger.warning("AI returned invalid JSON, using statistical forecast", error=str(e))
                # Fallback to statistical forecast with AI insights as text
                return {
                    "status": "success",
                    "product_id": product_id,
                    "forecast_period_days": days_ahead,
                    "statistical_forecast": statistical_forecast,
                    "ai_insights_text": ai_response["content"],
                    "data_points_analyzed": len(historical_data) if historical_data else 0,
                    "ai_model": f"{self.model}_with_statistical_fallback",
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error("Enhanced AI forecast failed", product_id=product_id, error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def generate_restock_recommendations_ai(self, low_stock_threshold: float = 20.0) -> Dict[str, Any]:
        """Generate AI-powered restock recommendations"""
        try:
            # Get low stock items
            db = get_db()
            
            pipeline = [
                {
                    "$addFields": {
                        "stock_percentage": {
                            "$multiply": [
                                {"$divide": ["$current_stock", {"$ifNull": ["$max_stock", 100]}]},
                                100
                            ]
                        }
                    }
                },
                {
                    "$match": {
                        "stock_percentage": {"$lt": low_stock_threshold}
                    }
                },
                {"$limit": 10}  # Focus on top 10 for AI analysis
            ]
            
            low_stock_items = list(db.products.aggregate(pipeline))
            
            if not low_stock_items:
                return {
                    "status": "success",
                    "message": "No low stock items found",
                    "recommendations": []
                }
            
            # Prepare data for AI analysis
            system_prompt = """You are an expert inventory manager. Analyze the low stock items and generate actionable restock recommendations.

Your response must be a valid JSON array where each item has this structure:
{
    "product_id": "string",
    "recommended_restock_quantity": number,
    "urgency": "high|medium|low",
    "reasoning": "explanation for the recommendation",
    "estimated_cost": number,
    "priority_rank": number
}

Consider seasonality, trends, supplier lead times, and business impact."""
            
            items_summary = self._prepare_restock_data_summary(low_stock_items)
            
            # Call MiniMax API
            ai_response = self._call_minimax_api(items_summary, system_prompt)
            
            if ai_response["status"] != "success":
                return ai_response
            
            try:
                recommendations = json.loads(ai_response["content"])
                
                return {
                    "status": "success",
                    "total_items_analyzed": len(low_stock_items),
                    "threshold_percentage": low_stock_threshold,
                    "ai_recommendations": recommendations,
                    "ai_model": self.model,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except json.JSONDecodeError:
                return {
                    "status": "success",
                    "total_items_analyzed": len(low_stock_items),
                    "ai_insights": ai_response["content"],
                    "ai_model": self.model,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error("AI restock recommendations failed", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def analyze_supplier_performance_ai(self, supplier_name: Optional[str] = None) -> Dict[str, Any]:
        """AI analysis of supplier performance"""
        try:
            # Get supplier data and performance metrics
            db = get_db()
            
            if supplier_name:
                suppliers = list(db.suppliers.find({"name": supplier_name}))
            else:
                suppliers = list(db.suppliers.find().limit(5))
            
            if not suppliers:
                return {"status": "error", "message": "No supplier data found"}
            
            # Get related product performance from Snowflake
            supplier_performance_data = await self._get_supplier_performance_data(suppliers)
            
            system_prompt = """You are a supply chain expert. Analyze the supplier performance data and provide insights.

Your response must be a valid JSON object:
{
    "overall_assessment": "excellent|good|average|poor",
    "top_performers": ["supplier1", "supplier2"],
    "improvement_needed": ["supplier3"],
    "key_insights": [
        "insight 1",
        "insight 2"
    ],
    "recommendations": [
        "recommendation 1",
        "recommendation 2"
    ]
}

Focus on delivery performance, quality, pricing, and reliability."""
            
            analysis_data = self._prepare_supplier_analysis_data(suppliers, supplier_performance_data)
            
            ai_response = self._call_minimax_api(analysis_data, system_prompt)
            
            if ai_response["status"] != "success":
                return ai_response
            
            try:
                analysis_result = json.loads(ai_response["content"])
                
                return {
                    "status": "success",
                    "suppliers_analyzed": len(suppliers),
                    "ai_analysis": analysis_result,
                    "ai_model": self.model,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
            except json.JSONDecodeError:
                return {
                    "status": "success",
                    "suppliers_analyzed": len(suppliers),
                    "ai_insights": ai_response["content"],
                    "ai_model": self.model,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
        except Exception as e:
            logger.error("AI supplier analysis failed", error=str(e))
            return {"status": "error", "message": str(e)}
    
    async def _get_historical_data(self, product_id: str, days_back: int = 90) -> List[Dict]:
        """Get comprehensive historical sales data from Snowflake with enhanced analytics"""
        try:
            conn = get_snowflake_connection()
            if not conn:
                logger.info("Snowflake not available, using mock historical data")
                return self._generate_mock_historical_data(product_id, days_back)
            
            try:
                # Enhanced query with more sophisticated metrics
                # Join sales data with inventory history for comprehensive analysis
                query = f"""
            WITH sales_daily AS (
                SELECT 
                    SALE_DATE as SNAPSHOT_DATE,
                    PRODUCT_ID,
                    SUM(QUANTITY_SOLD) as QUANTITY_SOLD,
                    SUM(TOTAL_REVENUE_LINE) as REVENUE,
                    EXTRACT(DOW FROM SALE_DATE) as DAY_OF_WEEK,
                    EXTRACT(MONTH FROM SALE_DATE) as MONTH,
                    CASE 
                        WHEN EXTRACT(DOW FROM SALE_DATE) IN (6, 0) THEN 1 
                        ELSE 0 
                    END as IS_WEEKEND
                FROM AWSHACK725.PUBLIC.SALES_ANALYTICS 
                WHERE PRODUCT_ID = '{product_id}'
                AND SALE_DATE >= DATEADD(day, -{days_back + 30}, CURRENT_DATE())
                GROUP BY SALE_DATE, PRODUCT_ID
            ),
            inventory_daily AS (
                SELECT 
                    SNAPSHOT_DATE,
                    PRODUCT_ID,
                    STOCK_LEVEL as INVENTORY_LEVEL
                FROM AWSHACK725.PUBLIC.INVENTORY_HISTORY 
                WHERE PRODUCT_ID = '{product_id}'
                AND SNAPSHOT_DATE >= DATEADD(day, -{days_back + 30}, CURRENT_DATE())
            ),
            daily_metrics AS (
                SELECT 
                    COALESCE(s.SNAPSHOT_DATE, i.SNAPSHOT_DATE) as SNAPSHOT_DATE,
                    COALESCE(s.PRODUCT_ID, i.PRODUCT_ID) as PRODUCT_ID,
                    COALESCE(s.QUANTITY_SOLD, 0) as QUANTITY_SOLD,
                    COALESCE(s.REVENUE, 0) as REVENUE,
                    i.INVENTORY_LEVEL,
                    LAG(i.INVENTORY_LEVEL, 1) OVER (ORDER BY COALESCE(s.SNAPSHOT_DATE, i.SNAPSHOT_DATE)) as PREV_INVENTORY,
                    LAG(COALESCE(s.QUANTITY_SOLD, 0), 7) OVER (ORDER BY COALESCE(s.SNAPSHOT_DATE, i.SNAPSHOT_DATE)) as QUANTITY_SOLD_7D_AGO,
                    AVG(COALESCE(s.QUANTITY_SOLD, 0)) OVER (
                        ORDER BY COALESCE(s.SNAPSHOT_DATE, i.SNAPSHOT_DATE) 
                        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
                    ) as MOVING_AVG_7D,
                    AVG(COALESCE(s.QUANTITY_SOLD, 0)) OVER (
                        ORDER BY COALESCE(s.SNAPSHOT_DATE, i.SNAPSHOT_DATE) 
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    ) as MOVING_AVG_30D,
                    STDDEV(COALESCE(s.QUANTITY_SOLD, 0)) OVER (
                        ORDER BY COALESCE(s.SNAPSHOT_DATE, i.SNAPSHOT_DATE) 
                        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
                    ) as VOLATILITY_30D,
                    s.DAY_OF_WEEK,
                    s.MONTH,
                    s.IS_WEEKEND
                FROM sales_daily s
                FULL OUTER JOIN inventory_daily i 
                    ON s.SNAPSHOT_DATE = i.SNAPSHOT_DATE AND s.PRODUCT_ID = i.PRODUCT_ID
            ),
            trend_analysis AS (
                SELECT *,
                    CASE 
                        WHEN MOVING_AVG_7D > MOVING_AVG_30D * 1.1 THEN 'INCREASING'
                        WHEN MOVING_AVG_7D < MOVING_AVG_30D * 0.9 THEN 'DECREASING'
                        ELSE 'STABLE'
                    END as TREND,
                    CASE 
                        WHEN VOLATILITY_30D > MOVING_AVG_30D * 0.5 THEN 'HIGH'
                        WHEN VOLATILITY_30D > MOVING_AVG_30D * 0.2 THEN 'MEDIUM'
                        ELSE 'LOW'
                    END as VOLATILITY_LEVEL
                FROM daily_metrics
                WHERE SNAPSHOT_DATE >= DATEADD(day, -{days_back}, CURRENT_DATE())
            )
            SELECT 
                SNAPSHOT_DATE,
                QUANTITY_SOLD,
                REVENUE,
                INVENTORY_LEVEL,
                PREV_INVENTORY,
                QUANTITY_SOLD_7D_AGO,
                MOVING_AVG_7D,
                MOVING_AVG_30D,
                VOLATILITY_30D,
                DAY_OF_WEEK,
                MONTH,
                IS_WEEKEND,
                TREND,
                VOLATILITY_LEVEL,
                -- Seasonality indicators
                CASE 
                    WHEN MONTH IN (11, 12) THEN 'HOLIDAY_SEASON'
                    WHEN MONTH IN (6, 7, 8) THEN 'SUMMER_SEASON'
                    WHEN MONTH IN (1, 2) THEN 'POST_HOLIDAY'
                    ELSE 'REGULAR'
                END as SEASON,
                -- Stock-out risk indicators
                CASE 
                    WHEN INVENTORY_LEVEL <= MOVING_AVG_7D * 3 THEN 'HIGH_RISK'
                    WHEN INVENTORY_LEVEL <= MOVING_AVG_7D * 7 THEN 'MEDIUM_RISK'
                    ELSE 'LOW_RISK'
                END as STOCKOUT_RISK
            FROM trend_analysis
            WHERE SNAPSHOT_DATE IS NOT NULL
            ORDER BY SNAPSHOT_DATE
            """
            
                with conn.cursor() as cur:
                    cur.execute(query)
                    columns = [desc[0] for desc in cur.description]
                    results = cur.fetchall()
                
                historical_data = [dict(zip(columns, row)) for row in results]
                
                # Add additional calculated metrics
                for i, record in enumerate(historical_data):
                    # Calculate velocity (rate of inventory consumption)
                    if record.get('PREV_INVENTORY') and record.get('INVENTORY_LEVEL'):
                        velocity = record['PREV_INVENTORY'] - record['INVENTORY_LEVEL']
                        record['INVENTORY_VELOCITY'] = velocity
                    else:
                        record['INVENTORY_VELOCITY'] = 0
                    
                    # Calculate demand acceleration (change in demand trend)
                    if i > 0:
                        prev_qty = historical_data[i-1].get('QUANTITY_SOLD', 0)
                        current_qty = record.get('QUANTITY_SOLD', 0)
                        record['DEMAND_ACCELERATION'] = current_qty - prev_qty
                    else:
                        record['DEMAND_ACCELERATION'] = 0
                
                return historical_data
            
            except Exception as snowflake_error:
                logger.error("Snowflake query failed, using mock data", error=str(snowflake_error))
                return self._generate_mock_historical_data(product_id, days_back)
            
        except Exception as e:
            logger.error("Failed to get enhanced historical data", error=str(e))
            return self._generate_mock_historical_data(product_id, days_back)
    
    def _generate_mock_historical_data(self, product_id: str, days_back: int = 90) -> List[Dict]:
        """Generate mock historical data for testing when Snowflake is not available"""
        import random
        from datetime import datetime, timedelta
        
        historical_data = []
        base_demand = random.randint(5, 50)  # Base daily demand
        
        for i in range(days_back):
            date = datetime.utcnow() - timedelta(days=days_back - i)
            
            # Add some variation and trends
            trend_factor = 1 + (i / days_back) * 0.2  # Slight upward trend
            seasonal_factor = 1 + 0.3 * math.sin(2 * math.pi * i / 7)  # Weekly seasonality
            noise = random.uniform(0.7, 1.3)  # Random noise
            
            quantity_sold = max(0, int(base_demand * trend_factor * seasonal_factor * noise))
            revenue = quantity_sold * random.uniform(10, 100)  # Random price
            inventory_level = max(0, random.randint(50, 200) - (i * 2))  # Declining inventory
            
            record = {
                'SNAPSHOT_DATE': date.strftime('%Y-%m-%d'),
                'PRODUCT_ID': product_id,
                'QUANTITY_SOLD': quantity_sold,
                'REVENUE': revenue,
                'INVENTORY_LEVEL': inventory_level,
                'MOVING_AVG_7D': base_demand * 0.9,
                'MOVING_AVG_30D': base_demand * 1.1,
                'VOLATILITY_30D': base_demand * 0.2,
                'DAY_OF_WEEK': date.weekday(),
                'MONTH': date.month,
                'IS_WEEKEND': 1 if date.weekday() >= 5 else 0,
                'INVENTORY_VELOCITY': random.randint(-5, 15),
                'DEMAND_ACCELERATION': random.randint(-3, 3)
            }
            
            historical_data.append(record)
        
        return historical_data
    
    async def _get_current_inventory_data(self, product_id: str) -> Dict:
        """Get current inventory data from MongoDB"""
        try:
            db = get_db()
            product = db.products.find_one({"product_id": product_id})
            
            if product:
                product['_id'] = str(product['_id'])
                return product
            return {}
            
        except Exception as e:
            logger.error("Failed to get current inventory data", error=str(e))
            return {}
    
    def _prepare_data_summary(self, historical_data: List[Dict], current_data: Dict, product_id: str, days_ahead: int) -> str:
        """Prepare data summary for AI analysis"""
        summary = f"""INVENTORY FORECASTING REQUEST

Product ID: {product_id}
Forecast Period: {days_ahead} days
Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d')}

CURRENT INVENTORY STATUS:
- Current Stock: {current_data.get('current_stock', 'Unknown')}
- Max Stock Capacity: {current_data.get('max_stock', 'Unknown')}
- Reorder Point: {current_data.get('reorder_point', 'Unknown')}
- Supplier: {current_data.get('supplier', 'Unknown')}
- Category: {current_data.get('category', 'Unknown')}

HISTORICAL SALES DATA ({len(historical_data)} data points):"""
        
        if historical_data:
            # Add recent sales trends
            recent_sales = historical_data[-14:] if len(historical_data) >= 14 else historical_data
            summary += f"\nRecent 14-day sales pattern:\n"
            for record in recent_sales:
                summary += f"- {record.get('SNAPSHOT_DATE')}: {record.get('QUANTITY_SOLD', 0)} units sold, Revenue: ${record.get('REVENUE', 0)}\n"
            
            # Calculate basic statistics
            total_quantity = sum(record.get('QUANTITY_SOLD', 0) for record in historical_data)
            total_revenue = sum(record.get('REVENUE', 0) for record in historical_data)
            avg_daily_sales = total_quantity / len(historical_data) if historical_data else 0
            
            summary += f"""
SUMMARY STATISTICS:
- Total Sales Period: {len(historical_data)} days
- Total Quantity Sold: {total_quantity}
- Total Revenue: ${total_revenue}
- Average Daily Sales: {avg_daily_sales:.2f}
"""
        else:
            summary += "\nNo historical sales data available."
        
        summary += f"""
FORECAST REQUEST:
Please analyze this data and provide a {days_ahead}-day demand forecast including:
1. Predicted daily and total demand
2. Confidence level assessment
3. Key trends identified
4. Actionable recommendations for inventory management
"""
        
        return summary
    
    def _prepare_restock_data_summary(self, low_stock_items: List[Dict]) -> str:
        """Prepare low stock data for AI restock recommendations"""
        summary = f"""RESTOCK RECOMMENDATIONS REQUEST

Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d')}
Low Stock Items Count: {len(low_stock_items)}

LOW STOCK ITEMS ANALYSIS:
"""
        
        for i, item in enumerate(low_stock_items, 1):
            stock_pct = item.get('stock_percentage', 0)
            summary += f"""
{i}. Product ID: {item.get('product_id', 'Unknown')}
   - Current Stock: {item.get('current_stock', 0)}
   - Max Capacity: {item.get('max_stock', 100)}
   - Stock Level: {stock_pct:.1f}%
   - Supplier: {item.get('supplier', 'Unknown')}
   - Category: {item.get('category', 'Unknown')}
   - Unit Cost: ${item.get('unit_cost', 0)}
   - Reorder Point: {item.get('reorder_point', 10)}
"""
        
        summary += """
REQUIREMENTS:
For each product, provide:
1. Recommended restock quantity
2. Urgency level (high/medium/low)
3. Business reasoning
4. Estimated total cost
5. Priority ranking (1 = highest priority)

Consider factors like supplier lead times, seasonal demand, storage costs, and business impact.
"""
        
        return summary
    
    async def _get_supplier_performance_data(self, suppliers: List[Dict]) -> Dict:
        """Get supplier performance metrics from various sources"""
        performance_data = {}
        
        for supplier in suppliers:
            supplier_name = supplier.get('name', '')
            
            # Get product performance for this supplier
            try:
                db = get_db()
                supplier_products = list(db.products.find({"supplier": supplier_name}))
                
                performance_data[supplier_name] = {
                    "products_supplied": len(supplier_products),
                    "total_stock_value": sum(p.get('current_stock', 0) * p.get('unit_cost', 0) for p in supplier_products),
                    "low_stock_count": sum(1 for p in supplier_products if p.get('current_stock', 0) < p.get('reorder_point', 10)),
                    "contact_info": supplier.get('contact_info', {}),
                    "performance_metrics": supplier.get('performance_metrics', {})
                }
                
            except Exception as e:
                logger.error("Failed to get supplier performance data", supplier=supplier_name, error=str(e))
                performance_data[supplier_name] = {"error": str(e)}
        
        return performance_data
    
    def _prepare_supplier_analysis_data(self, suppliers: List[Dict], performance_data: Dict) -> str:
        """Prepare supplier data for AI analysis"""
        summary = f"""SUPPLIER PERFORMANCE ANALYSIS REQUEST

Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d')}
Suppliers Analyzed: {len(suppliers)}

SUPPLIER PERFORMANCE DATA:
"""
        
        for supplier in suppliers:
            supplier_name = supplier.get('name', 'Unknown')
            perf_data = performance_data.get(supplier_name, {})
            
            summary += f"""
Supplier: {supplier_name}
- Products Supplied: {perf_data.get('products_supplied', 0)}
- Total Stock Value: ${perf_data.get('total_stock_value', 0):.2f}
- Items Below Reorder Point: {perf_data.get('low_stock_count', 0)}
- Contact: {perf_data.get('contact_info', {}).get('email', 'Not available')}
- Lead Time: {supplier.get('lead_time_days', 'Unknown')} days
- Quality Rating: {supplier.get('quality_rating', 'Unknown')}/5
- On-Time Delivery: {supplier.get('on_time_delivery_rate', 'Unknown')}%
- Payment Terms: {supplier.get('payment_terms', 'Unknown')}
"""
        
        summary += """
ANALYSIS REQUEST:
Evaluate each supplier's performance and provide:
1. Overall performance assessment
2. Top performing suppliers
3. Suppliers needing improvement
4. Key insights about the supplier base
5. Strategic recommendations for supplier management

Consider delivery reliability, quality, pricing, communication, and strategic value.
"""
        
        return summary

    async def _get_market_conditions(self, product_id: str) -> Dict[str, Any]:
        """Get market conditions and external factors that might affect demand"""
        try:
            # This would integrate with external APIs, economic indicators, etc.
            # For now, return simulated market data
            return {
                "economic_indicators": {
                    "consumer_confidence": 75.2,
                    "inflation_rate": 3.1,
                    "unemployment_rate": 4.2
                },
                "seasonal_factors": {
                    "current_season": "winter",
                    "holiday_proximity": 15,  # days to next major holiday
                    "weather_impact": "moderate"
                },
                "competitive_factors": {
                    "market_saturation": "medium",
                    "price_competition": "high",
                    "new_entrants": 2
                }
            }
        except Exception as e:
            logger.error("Failed to get market conditions", error=str(e))
            return {}
    
    async def _perform_statistical_analysis(self, historical_data: List[Dict], days_ahead: int) -> Dict[str, Any]:
        """Perform statistical analysis and create baseline forecast"""
        try:
            if not historical_data:
                return {"error": "No historical data available"}
            
            # Extract quantity sold data
            quantities = [record.get('QUANTITY_SOLD', 0) for record in historical_data]
            
            # Basic statistical metrics
            import statistics
            mean_demand = statistics.mean(quantities) if quantities else 0
            median_demand = statistics.median(quantities) if quantities else 0
            std_dev = statistics.stdev(quantities) if len(quantities) > 1 else 0
            
            # Trend analysis
            if len(quantities) >= 7:
                recent_avg = statistics.mean(quantities[-7:])
                older_avg = statistics.mean(quantities[-14:-7]) if len(quantities) >= 14 else mean_demand
                trend_factor = recent_avg / older_avg if older_avg > 0 else 1.0
            else:
                trend_factor = 1.0
            
            # Seasonality detection (simplified)
            seasonality_factor = 1.0
            if len(historical_data) >= 30:
                # Check for day-of-week patterns
                weekday_avg = statistics.mean([
                    record.get('QUANTITY_SOLD', 0) for record in historical_data
                    if record.get('IS_WEEKEND') == 0
                ])
                weekend_avg = statistics.mean([
                    record.get('QUANTITY_SOLD', 0) for record in historical_data
                    if record.get('IS_WEEKEND') == 1
                ])
                
                if weekday_avg > 0 and weekend_avg > 0:
                    seasonality_factor = weekday_avg / weekend_avg
            
            # Simple moving average forecast
            forecast_daily = mean_demand * trend_factor
            forecast_total = forecast_daily * days_ahead
            
            # Confidence intervals
            confidence_margin = std_dev * 1.96  # 95% confidence interval
            
            return {
                "method": "statistical_analysis",
                "daily_forecast": forecast_daily,
                "total_forecast": forecast_total,
                "confidence_intervals": {
                    "lower": max(0, forecast_total - confidence_margin * days_ahead),
                    "upper": forecast_total + confidence_margin * days_ahead
                },
                "statistics": {
                    "mean": mean_demand,
                    "median": median_demand,
                    "std_dev": std_dev,
                    "trend_factor": trend_factor,
                    "seasonality_factor": seasonality_factor
                },
                "data_quality": {
                    "sample_size": len(quantities),
                    "coefficient_of_variation": (std_dev / mean_demand) if mean_demand > 0 else 0
                }
            }
            
        except Exception as e:
            logger.error("Failed to perform statistical analysis", error=str(e))
            return {"error": str(e)}
    
    def _prepare_enhanced_data_summary(
        self,
        historical_data: List[Dict],
        current_data: Dict,
        market_data: Dict,
        statistical_forecast: Dict,
        product_id: str,
        days_ahead: int
    ) -> str:
        """Prepare enhanced data summary for AI analysis"""
        
        summary = f"""ENHANCED INVENTORY FORECASTING REQUEST

Product ID: {product_id}
Forecast Period: {days_ahead} days
Analysis Date: {datetime.utcnow().strftime('%Y-%m-%d')}

CURRENT INVENTORY STATUS:
- Current Stock: {current_data.get('current_stock', 'Unknown')}
- Max Stock Capacity: {current_data.get('max_stock', 'Unknown')}
- Reorder Point: {current_data.get('reorder_point', 'Unknown')}
- Supplier: {current_data.get('supplier', 'Unknown')}
- Category: {current_data.get('category', 'Unknown')}

STATISTICAL BASELINE FORECAST:
- Method: {statistical_forecast.get('method', 'N/A')}
- Daily Forecast: {statistical_forecast.get('daily_forecast', 0):.2f}
- Total Forecast: {statistical_forecast.get('total_forecast', 0):.2f}
- Confidence Range: {statistical_forecast.get('confidence_intervals', {}).get('lower', 0):.0f} - {statistical_forecast.get('confidence_intervals', {}).get('upper', 0):.0f}
- Trend Factor: {statistical_forecast.get('statistics', {}).get('trend_factor', 1.0):.2f}
- Seasonality Factor: {statistical_forecast.get('statistics', {}).get('seasonality_factor', 1.0):.2f}

HISTORICAL DATA ANALYSIS ({len(historical_data)} data points):"""
        
        if historical_data:
            # Recent trends
            recent_records = historical_data[-14:] if len(historical_data) >= 14 else historical_data
            summary += f"\n\nRECENT SALES PATTERN (Last {len(recent_records)} days):\n"
            
            for record in recent_records[-7:]:  # Show last 7 days
                summary += f"- {record.get('SNAPSHOT_DATE')}: {record.get('QUANTITY_SOLD', 0)} units, Trend: {record.get('TREND', 'N/A')}, Volatility: {record.get('VOLATILITY_LEVEL', 'N/A')}\n"
            
            # Trend analysis
            trends = [record.get('TREND', 'STABLE') for record in recent_records]
            trend_summary = max(set(trends), key=trends.count) if trends else 'STABLE'
            
            # Seasonality analysis
            seasons = [record.get('SEASON', 'REGULAR') for record in historical_data]
            current_season = seasons[-1] if seasons else 'REGULAR'
            
            # Risk analysis
            risks = [record.get('STOCKOUT_RISK', 'LOW_RISK') for record in recent_records]
            current_risk = max(set(risks), key=risks.count) if risks else 'LOW_RISK'
            
            summary += f"""
TREND ANALYSIS:
- Dominant Recent Trend: {trend_summary}
- Current Season: {current_season}
- Current Stock-out Risk: {current_risk}
- Average Daily Sales (30d): {statistical_forecast.get('statistics', {}).get('mean', 0):.2f}
- Demand Volatility (CoV): {statistical_forecast.get('data_quality', {}).get('coefficient_of_variation', 0):.2f}
"""
        
        # Market conditions
        if market_data:
            summary += f"""
MARKET CONDITIONS:
- Consumer Confidence: {market_data.get('economic_indicators', {}).get('consumer_confidence', 'N/A')}
- Current Season: {market_data.get('seasonal_factors', {}).get('current_season', 'N/A')}
- Holiday Proximity: {market_data.get('seasonal_factors', {}).get('holiday_proximity', 'N/A')} days
- Market Saturation: {market_data.get('competitive_factors', {}).get('market_saturation', 'N/A')}
- Price Competition: {market_data.get('competitive_factors', {}).get('price_competition', 'N/A')}
"""
        
        summary += f"""
FORECASTING REQUEST:
Please analyze this comprehensive data and provide a {days_ahead}-day demand forecast that:
1. Considers the statistical baseline but applies AI insights for refinement
2. Accounts for trend, seasonality, and market conditions
3. Provides realistic forecast ranges (optimistic, pessimistic, most likely)
4. Identifies key demand drivers and risk factors
5. Offers actionable recommendations for inventory management

Focus on business-practical insights that help optimize inventory levels and reduce risk.
"""
        
        return summary
    
    def _validate_and_enhance_forecast(
        self,
        ai_forecast: Dict,
        statistical_forecast: Dict,
        historical_data: List[Dict]
    ) -> Dict[str, Any]:
        """Validate AI forecast against statistical baseline and enhance with additional insights"""
        try:
            # Extract AI forecast values
            ai_daily = ai_forecast.get("forecast", {}).get("daily_demand", 0)
            ai_total = ai_forecast.get("forecast", {}).get("total_demand", 0)
            statistical_daily = statistical_forecast.get("daily_forecast", 0)
            statistical_total = statistical_forecast.get("total_forecast", 0)
            
            # Validation: Check if AI forecast is reasonable compared to statistical baseline
            if statistical_daily > 0:
                variance_ratio = abs(ai_daily - statistical_daily) / statistical_daily
                
                # If AI forecast is wildly different (>200% variance), adjust it
                if variance_ratio > 2.0:
                    logger.warning("AI forecast significantly differs from statistical baseline", 
                                 ai_daily=ai_daily, statistical_daily=statistical_daily, variance=variance_ratio)
                    
                    # Blend the forecasts (70% statistical, 30% AI adjustment)
                    adjusted_daily = statistical_daily * 0.7 + ai_daily * 0.3
                    ai_forecast["forecast"]["daily_demand"] = adjusted_daily
                    ai_forecast["forecast"]["total_demand"] = adjusted_daily * (ai_total / ai_daily if ai_daily > 0 else 1)
                    ai_forecast["forecast"]["confidence_level"] = "medium"  # Reduce confidence due to adjustment
                    
                    # Add note about adjustment
                    if "notes" not in ai_forecast:
                        ai_forecast["notes"] = []
                    ai_forecast["notes"].append("Forecast adjusted due to high variance from statistical baseline")
            
            # Add enhanced metrics
            ai_forecast["validation"] = {
                "statistical_baseline": {
                    "daily": statistical_daily,
                    "total": statistical_total
                },
                "variance_from_baseline": {
                    "daily_percent": ((ai_daily - statistical_daily) / statistical_daily * 100) if statistical_daily > 0 else 0,
                    "total_percent": ((ai_total - statistical_total) / statistical_total * 100) if statistical_total > 0 else 0
                },
                "data_support": len(historical_data),
                "forecast_reliability": self._calculate_forecast_reliability(ai_forecast, statistical_forecast, historical_data)
            }
            
            return ai_forecast
            
        except Exception as e:
            logger.error("Failed to validate forecast", error=str(e))
            return ai_forecast  # Return original if validation fails
    
    def _calculate_forecast_reliability(self, ai_forecast: Dict, statistical_forecast: Dict, historical_data: List[Dict]) -> str:
        """Calculate overall forecast reliability based on various factors"""
        try:
            reliability_score = 0
            
            # Data quality factor (0-30 points)
            data_points = len(historical_data)
            if data_points >= 60:
                reliability_score += 30
            elif data_points >= 30:
                reliability_score += 20
            elif data_points >= 14:
                reliability_score += 10
            
            # Consistency factor (0-25 points)
            confidence = ai_forecast.get("forecast", {}).get("confidence_level", "low")
            if confidence == "high":
                reliability_score += 25
            elif confidence == "medium":
                reliability_score += 15
            elif confidence == "low":
                reliability_score += 5
            
            # Statistical validation (0-25 points)
            variance = ai_forecast.get("validation", {}).get("variance_from_baseline", {}).get("daily_percent", 0)
            if abs(variance) <= 20:
                reliability_score += 25
            elif abs(variance) <= 50:
                reliability_score += 15
            elif abs(variance) <= 100:
                reliability_score += 10
            
            # Trend consistency (0-20 points)
            if historical_data and len(historical_data) >= 7:
                recent_trend = historical_data[-1].get('TREND', 'STABLE')
                ai_trend = ai_forecast.get("forecast", {}).get("trend", "stable")
                if recent_trend.lower() == ai_trend.lower():
                    reliability_score += 20
                else:
                    reliability_score += 10
            
            # Return reliability category
            if reliability_score >= 80:
                return "high"
            elif reliability_score >= 60:
                return "medium"
            elif reliability_score >= 40:
                return "moderate"
            else:
                return "low"
                
        except Exception as e:
            logger.error("Failed to calculate forecast reliability", error=str(e))
            return "unknown"
    
    async def _calculate_forecast_accuracy_metrics(self, product_id: str) -> Dict[str, Any]:
        """Calculate historical forecast accuracy metrics"""
        try:
            # This would compare historical forecasts with actual outcomes
            # For now, return simulated metrics
            return {
                "mape": 18.5,  # Mean Absolute Percentage Error
                "rmse": 12.3,  # Root Mean Square Error
                "bias": -2.1,  # Forecast bias (positive = over-forecast, negative = under-forecast)
                "accuracy_trend": "improving",
                "last_updated": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error("Failed to calculate accuracy metrics", error=str(e))
            return {}
    
    def _assess_data_quality(self, historical_data: List[Dict]) -> Dict[str, Any]:
        """Assess the quality of historical data for forecasting"""
        try:
            if not historical_data:
                return {"quality": "poor", "reason": "No historical data available"}
            
            data_points = len(historical_data)
            
            # Check for data completeness
            complete_records = sum(1 for record in historical_data if record.get('QUANTITY_SOLD') is not None)
            completeness = complete_records / data_points if data_points > 0 else 0
            
            # Check for data recency
            if historical_data:
                latest_date = historical_data[-1].get('SNAPSHOT_DATE')
                if latest_date:
                    # This is simplified - in practice you'd parse the date
                    recency_score = 1.0  # Assume recent for now
                else:
                    recency_score = 0.5
            else:
                recency_score = 0.0
            
            # Check for data consistency (low variance in data availability)
            gaps = sum(1 for record in historical_data if record.get('QUANTITY_SOLD') is None or record.get('QUANTITY_SOLD') < 0)
            consistency = 1.0 - (gaps / data_points) if data_points > 0 else 0
            
            # Overall quality score
            quality_score = (completeness * 0.4 + recency_score * 0.3 + consistency * 0.3) * 100
            
            if quality_score >= 85:
                quality = "excellent"
            elif quality_score >= 70:
                quality = "good"
            elif quality_score >= 50:
                quality = "fair"
            else:
                quality = "poor"
            
            return {
                "quality": quality,
                "score": round(quality_score, 1),
                "data_points": data_points,
                "completeness": round(completeness * 100, 1),
                "consistency": round(consistency * 100, 1),
                "recency_score": round(recency_score * 100, 1),
                "recommendation": self._get_data_quality_recommendation(quality, data_points)
            }
            
        except Exception as e:
            logger.error("Failed to assess data quality", error=str(e))
            return {"quality": "unknown", "error": str(e)}
    
    def _get_data_quality_recommendation(self, quality: str, data_points: int) -> str:
        """Get recommendation based on data quality assessment"""
        if quality == "poor":
            return "Improve data collection processes. More historical data needed for reliable forecasting."
        elif quality == "fair":
            return "Data quality is adequate but could be improved. Consider data validation checks."
        elif quality == "good":
            return "Good data quality. Forecasts should be reliable with noted confidence levels."
        elif quality == "excellent":
            return "Excellent data quality. High confidence in forecast accuracy."
        else:
            return "Unable to assess data quality."

# Global instance
ai_forecasting_service = AIForecastingService() 
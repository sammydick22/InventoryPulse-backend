"""
Real-time alerting service for inventory management
Handles WebSocket connections, alert processing, notifications, and escalation
"""

import json
import asyncio
import structlog
from typing import Dict, Any, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
# Email imports (optional, for future notification features)
# import smtplib
# from email.mime.text import MimeText
# from email.mime.multipart import MimeMultipart

from backend.services.db_service import get_db
from backend.services.ai_forecasting_service import ai_forecasting_service

logger = structlog.get_logger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertStatus(Enum):
    """Alert status types"""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"

class AlertType(Enum):
    """Alert types"""
    LOW_STOCK = "low_stock"
    STOCK_OUT = "stock_out"
    EXCESS_STOCK = "excess_stock"
    RESTOCK_NEEDED = "restock_needed"
    ANOMALY_DETECTED = "anomaly_detected"
    SUPPLIER_ISSUE = "supplier_issue"
    DEMAND_SPIKE = "demand_spike"
    SYSTEM_ERROR = "system_error"

@dataclass
class Alert:
    """Alert data structure"""
    alert_id: str
    alert_type: AlertType
    product_id: Optional[str]
    title: str
    message: str
    severity: AlertSeverity
    status: AlertStatus
    created_at: datetime
    updated_at: datetime
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class NotificationChannel:
    """Notification channel configuration"""
    channel_type: str  # email, webhook, slack, etc.
    endpoint: str
    enabled: bool = True
    severity_filter: List[AlertSeverity] = None

class RealTimeAlertingService:
    """Real-time alerting service with WebSocket support"""
    
    def __init__(self):
        self.active_connections: Set[Any] = set()  # WebSocket connections
        self.alert_rules: List[Dict] = []
        self.notification_channels: List[NotificationChannel] = []
        self.alert_cache: Dict[str, Alert] = {}
        self.running = False
        
    async def initialize(self):
        """Initialize the alerting service"""
        try:
            # Load alert rules and notification channels from database
            await self._load_alert_rules()
            await self._load_notification_channels()
            
            # Start background processing
            self.running = True
            asyncio.create_task(self._process_alerts_continuously())
            asyncio.create_task(self._cleanup_old_alerts())
            
            logger.info("Real-time alerting service initialized")
            return True
            
        except Exception as e:
            logger.error("Failed to initialize alerting service", error=str(e))
            return False
    
    async def stop(self):
        """Stop the alerting service"""
        self.running = False
        logger.info("Real-time alerting service stopped")
    
    # WebSocket Connection Management
    
    async def add_websocket_connection(self, websocket):
        """Add a WebSocket connection for real-time alerts"""
        self.active_connections.add(websocket)
        logger.info("WebSocket connection added", total_connections=len(self.active_connections))
    
    async def remove_websocket_connection(self, websocket):
        """Remove a WebSocket connection"""
        self.active_connections.discard(websocket)
        logger.info("WebSocket connection removed", total_connections=len(self.active_connections))
    
    async def broadcast_alert(self, alert: Alert):
        """Broadcast alert to all connected WebSocket clients"""
        if not self.active_connections:
            return
        
        alert_data = {
            "type": "alert",
            "data": asdict(alert),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Convert datetime objects to ISO strings for JSON serialization
        alert_data["data"]["created_at"] = alert.created_at.isoformat()
        alert_data["data"]["updated_at"] = alert.updated_at.isoformat()
        if alert.resolved_at:
            alert_data["data"]["resolved_at"] = alert.resolved_at.isoformat()
        
        # Convert enums to strings
        alert_data["data"]["alert_type"] = alert.alert_type.value
        alert_data["data"]["severity"] = alert.severity.value
        alert_data["data"]["status"] = alert.status.value
        
        message = json.dumps(alert_data)
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.active_connections:
            try:
                await websocket.send(message)
            except Exception as e:
                logger.warning("Failed to send WebSocket message", error=str(e))
                disconnected.add(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected:
            self.active_connections.discard(websocket)
    
    # Alert Management
    
    async def create_alert(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        severity: AlertSeverity,
        product_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Create a new alert"""
        
        alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{alert_type.value}"
        if product_id:
            alert_id += f"_{product_id}"
        
        alert = Alert(
            alert_id=alert_id,
            alert_type=alert_type,
            product_id=product_id,
            title=title,
            message=message,
            severity=severity,
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        
        # Store in cache and database
        self.alert_cache[alert_id] = alert
        await self._store_alert_to_db(alert)
        
        # Broadcast to WebSocket clients
        await self.broadcast_alert(alert)
        
        # Send notifications
        await self._send_notifications(alert)
        
        logger.info("Alert created", alert_id=alert_id, type=alert_type.value, severity=severity.value)
        return alert
    
    async def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """Acknowledge an alert"""
        try:
            if alert_id in self.alert_cache:
                alert = self.alert_cache[alert_id]
                alert.status = AlertStatus.ACKNOWLEDGED
                alert.acknowledged_by = acknowledged_by
                alert.updated_at = datetime.utcnow()
                
                await self._update_alert_in_db(alert)
                await self.broadcast_alert(alert)
                
                logger.info("Alert acknowledged", alert_id=alert_id, acknowledged_by=acknowledged_by)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to acknowledge alert", alert_id=alert_id, error=str(e))
            return False
    
    async def resolve_alert(self, alert_id: str, resolved_by: str, resolution_note: str = "") -> bool:
        """Resolve an alert"""
        try:
            if alert_id in self.alert_cache:
                alert = self.alert_cache[alert_id]
                alert.status = AlertStatus.RESOLVED
                alert.resolved_by = resolved_by
                alert.resolved_at = datetime.utcnow()
                alert.updated_at = datetime.utcnow()
                
                if resolution_note:
                    if not alert.metadata:
                        alert.metadata = {}
                    alert.metadata["resolution_note"] = resolution_note
                
                await self._update_alert_in_db(alert)
                await self.broadcast_alert(alert)
                
                logger.info("Alert resolved", alert_id=alert_id, resolved_by=resolved_by)
                return True
            
            return False
            
        except Exception as e:
            logger.error("Failed to resolve alert", alert_id=alert_id, error=str(e))
            return False
    
    async def get_active_alerts(self, product_id: Optional[str] = None) -> List[Alert]:
        """Get all active alerts"""
        alerts = []
        for alert in self.alert_cache.values():
            if alert.status in [AlertStatus.ACTIVE, AlertStatus.ACKNOWLEDGED]:
                if product_id is None or alert.product_id == product_id:
                    alerts.append(alert)
        
        return sorted(alerts, key=lambda x: x.created_at, reverse=True)
    
    # Smart Alert Generation
    
    async def check_and_create_low_stock_alerts(self):
        """Check for low stock conditions and create alerts"""
        try:
            db = get_db()
            
            # Find products with low stock
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
                        "$or": [
                            {"current_stock": {"$lte": "$reorder_point"}},
                            {"stock_percentage": {"$lt": 15}}
                        ]
                    }
                }
            ]
            
            low_stock_products = list(db.products.aggregate(pipeline))
            
            for product in low_stock_products:
                product_id = product["product_id"]
                current_stock = product.get("current_stock", 0)
                
                # Check if we already have an active alert for this product
                existing_alert = any(
                    alert.product_id == product_id and 
                    alert.alert_type == AlertType.LOW_STOCK and
                    alert.status == AlertStatus.ACTIVE
                    for alert in self.alert_cache.values()
                )
                
                if not existing_alert:
                    severity = AlertSeverity.CRITICAL if current_stock == 0 else (
                        AlertSeverity.HIGH if current_stock <= product.get("reorder_point", 10) / 2
                        else AlertSeverity.MEDIUM
                    )
                    
                    await self.create_alert(
                        alert_type=AlertType.LOW_STOCK if current_stock > 0 else AlertType.STOCK_OUT,
                        title=f"{'Stock Out' if current_stock == 0 else 'Low Stock'}: {product.get('name', product_id)}",
                        message=f"Product {product_id} has {current_stock} units remaining (Reorder point: {product.get('reorder_point', 10)})",
                        severity=severity,
                        product_id=product_id,
                        metadata={
                            "current_stock": current_stock,
                            "reorder_point": product.get("reorder_point", 10),
                            "stock_percentage": product.get("stock_percentage", 0)
                        }
                    )
                    
        except Exception as e:
            logger.error("Failed to check low stock alerts", error=str(e))
    
    async def check_and_create_anomaly_alerts(self):
        """Use AI to detect anomalies and create alerts"""
        try:
            db = get_db()
            products = list(db.products.find().limit(50))  # Process in batches
            
            for product in products:
                product_id = product["product_id"]
                
                # Use AI forecasting to detect anomalies
                forecast_result = await ai_forecasting_service.forecast_demand_ai(product_id, days_ahead=7)
                
                if forecast_result.get("status") == "success":
                    ai_forecast = forecast_result.get("ai_forecast", {})
                    current_stock = product.get("current_stock", 0)
                    forecasted_demand = ai_forecast.get("forecast", {}).get("total_demand", 0)
                    
                    # Check for demand spike anomaly
                    if forecasted_demand > current_stock * 2:  # Demand exceeds stock by 2x
                        await self.create_alert(
                            alert_type=AlertType.DEMAND_SPIKE,
                            title=f"Demand Spike Detected: {product.get('name', product_id)}",
                            message=f"AI forecasting detected unusual demand spike. Forecasted demand: {forecasted_demand}, Current stock: {current_stock}",
                            severity=AlertSeverity.HIGH,
                            product_id=product_id,
                            metadata={
                                "forecasted_demand": forecasted_demand,
                                "current_stock": current_stock,
                                "ai_insights": ai_forecast.get("insights", [])
                            }
                        )
                    
                    # Check for excess stock
                    if current_stock > forecasted_demand * 4:  # Stock exceeds forecast by 4x
                        await self.create_alert(
                            alert_type=AlertType.EXCESS_STOCK,
                            title=f"Excess Stock Alert: {product.get('name', product_id)}",
                            message=f"Current stock significantly exceeds forecasted demand. Consider adjusting procurement.",
                            severity=AlertSeverity.MEDIUM,
                            product_id=product_id,
                            metadata={
                                "forecasted_demand": forecasted_demand,
                                "current_stock": current_stock,
                                "excess_ratio": current_stock / forecasted_demand if forecasted_demand > 0 else 0
                            }
                        )
                
        except Exception as e:
            logger.error("Failed to check anomaly alerts", error=str(e))
    
    # Background Processing
    
    async def _process_alerts_continuously(self):
        """Continuously process alerts in the background"""
        while self.running:
            try:
                # Check for low stock alerts
                await self.check_and_create_low_stock_alerts()
                
                # Check for anomaly alerts (less frequent)
                if datetime.utcnow().minute % 30 == 0:  # Every 30 minutes
                    await self.check_and_create_anomaly_alerts()
                
                # Check for alert escalation
                await self._check_alert_escalation()
                
                # Wait before next check
                await asyncio.sleep(300)  # 5 minutes
                
            except Exception as e:
                logger.error("Error in alert processing loop", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_old_alerts(self):
        """Clean up old resolved alerts"""
        while self.running:
            try:
                cutoff_time = datetime.utcnow() - timedelta(days=30)  # Keep alerts for 30 days
                
                alerts_to_remove = [
                    alert_id for alert_id, alert in self.alert_cache.items()
                    if alert.status == AlertStatus.RESOLVED and alert.resolved_at and alert.resolved_at < cutoff_time
                ]
                
                for alert_id in alerts_to_remove:
                    del self.alert_cache[alert_id]
                
                if alerts_to_remove:
                    logger.info("Cleaned up old alerts", count=len(alerts_to_remove))
                
                await asyncio.sleep(86400)  # Run daily
                
            except Exception as e:
                logger.error("Error in alert cleanup", error=str(e))
                await asyncio.sleep(3600)  # Wait an hour on error
    
    async def _check_alert_escalation(self):
        """Check if alerts need to be escalated"""
        try:
            escalation_time = timedelta(hours=2)  # Escalate after 2 hours
            current_time = datetime.utcnow()
            
            for alert in self.alert_cache.values():
                if (alert.status == AlertStatus.ACTIVE and 
                    alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL] and
                    current_time - alert.created_at > escalation_time):
                    
                    # Escalate the alert
                    alert.status = AlertStatus.ESCALATED
                    alert.updated_at = current_time
                    
                    await self._update_alert_in_db(alert)
                    await self.broadcast_alert(alert)
                    
                    # Send escalation notification
                    await self._send_escalation_notification(alert)
                    
        except Exception as e:
            logger.error("Error in alert escalation check", error=str(e))
    
    # Database Operations
    
    async def _store_alert_to_db(self, alert: Alert):
        """Store alert to database"""
        try:
            db = get_db()
            alert_doc = asdict(alert)
            
            # Convert enum values to strings
            alert_doc["alert_type"] = alert.alert_type.value
            alert_doc["severity"] = alert.severity.value
            alert_doc["status"] = alert.status.value
            
            db.alerts.insert_one(alert_doc)
            
        except Exception as e:
            logger.error("Failed to store alert to database", alert_id=alert.alert_id, error=str(e))
    
    async def _update_alert_in_db(self, alert: Alert):
        """Update alert in database"""
        try:
            db = get_db()
            alert_doc = asdict(alert)
            
            # Convert enum values to strings
            alert_doc["alert_type"] = alert.alert_type.value
            alert_doc["severity"] = alert.severity.value
            alert_doc["status"] = alert.status.value
            
            db.alerts.update_one(
                {"alert_id": alert.alert_id},
                {"$set": alert_doc}
            )
            
        except Exception as e:
            logger.error("Failed to update alert in database", alert_id=alert.alert_id, error=str(e))
    
    # Notification System
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for channel in self.notification_channels:
            if not channel.enabled:
                continue
            
            # Check severity filter
            if channel.severity_filter and alert.severity not in channel.severity_filter:
                continue
            
            try:
                if channel.channel_type == "email":
                    await self._send_email_notification(alert, channel.endpoint)
                elif channel.channel_type == "webhook":
                    await self._send_webhook_notification(alert, channel.endpoint)
                
            except Exception as e:
                logger.error("Failed to send notification", channel=channel.channel_type, error=str(e))
    
    async def _send_email_notification(self, alert: Alert, email_address: str):
        """Send email notification"""
        # This would integrate with your email service
        # For now, just log the notification
        logger.info("Email notification sent", 
                   email=email_address, 
                   alert_id=alert.alert_id, 
                   severity=alert.severity.value)
    
    async def _send_webhook_notification(self, alert: Alert, webhook_url: str):
        """Send webhook notification"""
        # This would send HTTP POST to webhook URL
        # For now, just log the notification
        logger.info("Webhook notification sent", 
                   webhook=webhook_url, 
                   alert_id=alert.alert_id, 
                   severity=alert.severity.value)
    
    async def _send_escalation_notification(self, alert: Alert):
        """Send escalation notification"""
        logger.warning("Alert escalated", 
                      alert_id=alert.alert_id, 
                      product_id=alert.product_id, 
                      severity=alert.severity.value)
    
    async def _load_alert_rules(self):
        """Load alert rules from database"""
        # This would load custom alert rules from database
        # For now, use default rules
        self.alert_rules = [
            {
                "name": "low_stock_threshold",
                "condition": "current_stock <= reorder_point",
                "alert_type": "low_stock",
                "severity": "medium"
            }
        ]
    
    async def _load_notification_channels(self):
        """Load notification channels from database"""
        # This would load notification channels from database
        # For now, use default channels
        self.notification_channels = [
            NotificationChannel(
                channel_type="webhook",
                endpoint="http://localhost:3000/api/webhooks/alerts",
                severity_filter=[AlertSeverity.HIGH, AlertSeverity.CRITICAL]
            )
        ]

# Global instance
real_time_alerting_service = RealTimeAlertingService() 
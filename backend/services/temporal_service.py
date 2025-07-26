"""
Temporal workflows for real-time inventory processing
Handles automated inventory monitoring, restock workflows, and anomaly detection
"""

import asyncio
import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from temporalio import workflow, activity, common
from temporalio.client import Client
from temporalio.worker import Worker

from backend.services.db_service import get_db
from backend.services.ai_forecasting_service import ai_forecasting_service
from backend.services.mcp_service import mcp_server

logger = structlog.get_logger(__name__)

@dataclass
class InventoryWorkflowInput:
    """Input data for inventory workflows"""
    product_id: str
    check_interval_minutes: int = 60
    low_stock_threshold: float = 20.0
    auto_restock: bool = False

@dataclass
class AlertWorkflowInput:
    """Input data for alert workflows"""
    alert_types: List[str]
    check_interval_minutes: int = 30
    severity_threshold: str = "medium"

class TemporalInventoryService:
    """Temporal service for inventory workflows"""
    
    def __init__(self):
        self.client: Optional[Client] = None
        self.worker: Optional[Worker] = None
        self.task_queue = "inventory-processing"
    
    async def initialize(self, temporal_endpoint: str = "localhost:7233"):
        """Initialize Temporal client and worker"""
        try:
            self.client = await Client.connect(temporal_endpoint)
            logger.info("Connected to Temporal server", endpoint=temporal_endpoint)
            
            # Create worker for running workflows and activities
            self.worker = Worker(
                self.client,
                task_queue=self.task_queue,
                workflows=[
                    InventoryMonitoringWorkflow,
                    RestockWorkflow,
                    AnomalyDetectionWorkflow,
                    AlertProcessingWorkflow
                ],
                activities=[
                    check_inventory_levels,
                    generate_restock_recommendations,
                    detect_inventory_anomalies,
                    process_alerts,
                    send_notification,
                    update_inventory_status,
                    calculate_demand_forecast
                ]
            )
            
            return True
            
        except Exception as e:
            logger.error("Failed to initialize Temporal service", error=str(e))
            return False
    
    async def start_worker(self):
        """Start the Temporal worker"""
        if self.worker:
            logger.info("Starting Temporal worker")
            await self.worker.run()
    
    async def start_inventory_monitoring(self, product_id: str, check_interval: int = 60) -> str:
        """Start inventory monitoring workflow for a product"""
        if not self.client:
            raise Exception("Temporal client not initialized")
        
        workflow_id = f"inventory-monitor-{product_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        await self.client.start_workflow(
            InventoryMonitoringWorkflow.run,
            InventoryWorkflowInput(
                product_id=product_id,
                check_interval_minutes=check_interval
            ),
            id=workflow_id,
            task_queue=self.task_queue
        )
        
        logger.info("Started inventory monitoring workflow", workflow_id=workflow_id, product_id=product_id)
        return workflow_id
    
    async def start_restock_workflow(self, product_id: str, quantity: int, urgency: str = "medium") -> str:
        """Start restock workflow for a product"""
        if not self.client:
            raise Exception("Temporal client not initialized")
        
        workflow_id = f"restock-{product_id}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        await self.client.start_workflow(
            RestockWorkflow.run,
            {
                "product_id": product_id,
                "quantity": quantity,
                "urgency": urgency,
                "initiated_at": datetime.utcnow().isoformat()
            },
            id=workflow_id,
            task_queue=self.task_queue
        )
        
        logger.info("Started restock workflow", workflow_id=workflow_id, product_id=product_id, quantity=quantity)
        return workflow_id
    
    async def start_anomaly_detection(self, check_interval: int = 30) -> str:
        """Start anomaly detection workflow"""
        if not self.client:
            raise Exception("Temporal client not initialized")
        
        workflow_id = f"anomaly-detection-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        await self.client.start_workflow(
            AnomalyDetectionWorkflow.run,
            {"check_interval_minutes": check_interval},
            id=workflow_id,
            task_queue=self.task_queue
        )
        
        logger.info("Started anomaly detection workflow", workflow_id=workflow_id)
        return workflow_id

# Workflow Definitions

@workflow.defn
class InventoryMonitoringWorkflow:
    """Workflow for continuous inventory monitoring"""
    
    @workflow.run
    async def run(self, input_data: InventoryWorkflowInput) -> Dict[str, Any]:
        """Main workflow execution"""
        workflow.logger.info(f"Starting inventory monitoring for product {input_data.product_id}")
        
        while True:
            # Check inventory levels
            inventory_status = await workflow.execute_activity(
                check_inventory_levels,
                input_data.product_id,
                start_to_close_timeout=timedelta(seconds=30)
            )
            
            # Process the status and take actions
            if inventory_status.get("needs_attention"):
                # Generate alerts if needed
                if inventory_status.get("low_stock", False):
                    await workflow.execute_activity(
                        send_notification,
                        {
                            "type": "low_stock",
                            "product_id": input_data.product_id,
                            "current_stock": inventory_status.get("current_stock"),
                            "threshold": input_data.low_stock_threshold
                        },
                        start_to_close_timeout=timedelta(seconds=15)
                    )
                
                # Auto-generate restock recommendations
                if input_data.auto_restock:
                    restock_rec = await workflow.execute_activity(
                        generate_restock_recommendations,
                        input_data.product_id,
                        start_to_close_timeout=timedelta(seconds=60)
                    )
                    
                    if restock_rec.get("urgent", False):
                        # Start restock workflow
                        await workflow.start_child_workflow(
                            RestockWorkflow.run,
                            {
                                "product_id": input_data.product_id,
                                "quantity": restock_rec.get("recommended_quantity", 100),
                                "urgency": "high",
                                "initiated_by": "auto_monitor"
                            }
                        )
            
            # Wait for next check interval
            await asyncio.sleep(input_data.check_interval_minutes * 60)

@workflow.defn
class RestockWorkflow:
    """Workflow for handling restock processes"""
    
    @workflow.run
    async def run(self, restock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute restock workflow"""
        workflow.logger.info(f"Starting restock workflow for product {restock_data['product_id']}")
        
        # Calculate optimal restock quantity using AI
        forecast_data = await workflow.execute_activity(
            calculate_demand_forecast,
            restock_data["product_id"],
            start_to_close_timeout=timedelta(seconds=120)
        )
        
        # Generate purchase order or restock notification
        notification_result = await workflow.execute_activity(
            send_notification,
            {
                "type": "restock_needed",
                "product_id": restock_data["product_id"],
                "recommended_quantity": restock_data["quantity"],
                "urgency": restock_data["urgency"],
                "forecast_data": forecast_data
            },
            start_to_close_timeout=timedelta(seconds=30)
        )
        
        # Update inventory status
        await workflow.execute_activity(
            update_inventory_status,
            {
                "product_id": restock_data["product_id"],
                "status": "restock_pending",
                "restock_quantity": restock_data["quantity"]
            },
            start_to_close_timeout=timedelta(seconds=15)
        )
        
        return {
            "status": "completed",
            "product_id": restock_data["product_id"],
            "restock_quantity": restock_data["quantity"],
            "forecast_used": forecast_data
        }

@workflow.defn
class AnomalyDetectionWorkflow:
    """Workflow for detecting inventory anomalies"""
    
    @workflow.run
    async def run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run anomaly detection continuously"""
        workflow.logger.info("Starting anomaly detection workflow")
        
        while True:
            # Detect anomalies across all products
            anomalies = await workflow.execute_activity(
                detect_inventory_anomalies,
                {},
                start_to_close_timeout=timedelta(seconds=180)
            )
            
            # Process each anomaly
            for anomaly in anomalies.get("detected_anomalies", []):
                await workflow.execute_activity(
                    send_notification,
                    {
                        "type": "anomaly_detected",
                        "anomaly_data": anomaly,
                        "severity": anomaly.get("severity", "medium")
                    },
                    start_to_close_timeout=timedelta(seconds=30)
                )
            
            # Wait for next check
            await asyncio.sleep(config.get("check_interval_minutes", 30) * 60)

@workflow.defn
class AlertProcessingWorkflow:
    """Workflow for processing and managing alerts"""
    
    @workflow.run
    async def run(self, alert_config: AlertWorkflowInput) -> Dict[str, Any]:
        """Process alerts continuously"""
        workflow.logger.info("Starting alert processing workflow")
        
        while True:
            # Process pending alerts
            processed_alerts = await workflow.execute_activity(
                process_alerts,
                {
                    "alert_types": alert_config.alert_types,
                    "severity_threshold": alert_config.severity_threshold
                },
                start_to_close_timeout=timedelta(seconds=60)
            )
            
            # Wait for next processing cycle
            await asyncio.sleep(alert_config.check_interval_minutes * 60)

# Activity Definitions

@activity.defn
async def check_inventory_levels(product_id: str) -> Dict[str, Any]:
    """Activity to check current inventory levels"""
    try:
        result = await mcp_server.get_inventory(product_id=product_id)
        
        if result["status"] == "success" and result["products"]:
            product = result["products"][0]
            current_stock = product.get("current_stock", 0)
            reorder_point = product.get("reorder_point", 10)
            max_stock = product.get("max_stock", 100)
            
            stock_percentage = (current_stock / max_stock) * 100 if max_stock > 0 else 0
            
            return {
                "product_id": product_id,
                "current_stock": current_stock,
                "stock_percentage": stock_percentage,
                "low_stock": current_stock <= reorder_point,
                "needs_attention": current_stock <= reorder_point or stock_percentage < 20,
                "status": "success"
            }
        
        return {"status": "error", "message": "Product not found"}
        
    except Exception as e:
        logger.error("Failed to check inventory levels", product_id=product_id, error=str(e))
        return {"status": "error", "message": str(e)}

@activity.defn
async def generate_restock_recommendations(product_id: str) -> Dict[str, Any]:
    """Activity to generate AI-powered restock recommendations"""
    try:
        result = await mcp_server.recommend_restock(product_id=product_id)
        
        if result["status"] == "success" and result["recommendations"]:
            rec = result["recommendations"][0]
            return {
                "product_id": product_id,
                "recommended_quantity": rec.get("recommended_restock", 0),
                "urgency": rec.get("urgency", "medium"),
                "urgent": rec.get("urgency") == "high",
                "status": "success"
            }
        
        return {"status": "no_recommendations", "recommended_quantity": 0}
        
    except Exception as e:
        logger.error("Failed to generate restock recommendations", product_id=product_id, error=str(e))
        return {"status": "error", "message": str(e)}

@activity.defn
async def detect_inventory_anomalies() -> Dict[str, Any]:
    """Activity to detect inventory anomalies using AI"""
    try:
        # Get all inventory data
        inventory_result = await mcp_server.get_inventory()
        
        if inventory_result["status"] != "success":
            return {"status": "error", "message": "Failed to get inventory data"}
        
        anomalies = []
        products = inventory_result["products"]
        
        for product in products:
            current_stock = product.get("current_stock", 0)
            max_stock = product.get("max_stock", 100)
            reorder_point = product.get("reorder_point", 10)
            
            # Detect various anomaly types
            if current_stock < 0:
                anomalies.append({
                    "type": "negative_stock",
                    "product_id": product["product_id"],
                    "current_stock": current_stock,
                    "severity": "high"
                })
            
            if current_stock > max_stock * 1.5:
                anomalies.append({
                    "type": "excess_stock",
                    "product_id": product["product_id"],
                    "current_stock": current_stock,
                    "max_stock": max_stock,
                    "severity": "medium"
                })
            
            if current_stock == 0 and reorder_point > 0:
                anomalies.append({
                    "type": "stock_out",
                    "product_id": product["product_id"],
                    "severity": "high"
                })
        
        return {
            "status": "success",
            "detected_anomalies": anomalies,
            "total_products_checked": len(products)
        }
        
    except Exception as e:
        logger.error("Failed to detect anomalies", error=str(e))
        return {"status": "error", "message": str(e)}

@activity.defn
async def process_alerts(config: Dict[str, Any]) -> Dict[str, Any]:
    """Activity to process pending alerts"""
    try:
        # Implementation for alert processing
        # This would integrate with your existing alert system
        return {"status": "success", "processed_count": 0}
        
    except Exception as e:
        logger.error("Failed to process alerts", error=str(e))
        return {"status": "error", "message": str(e)}

@activity.defn
async def send_notification(notification_data: Dict[str, Any]) -> Dict[str, Any]:
    """Activity to send notifications/alerts"""
    try:
        # Create alert in the system
        result = await mcp_server.create_alert(
            alert_type=notification_data["type"],
            product_id=notification_data.get("product_id", "system"),
            message=f"Notification: {notification_data}",
            severity=notification_data.get("severity", "medium")
        )
        
        logger.info("Notification sent", notification_data=notification_data, result=result)
        return {"status": "success", "notification_sent": True}
        
    except Exception as e:
        logger.error("Failed to send notification", error=str(e))
        return {"status": "error", "message": str(e)}

@activity.defn
async def update_inventory_status(status_data: Dict[str, Any]) -> Dict[str, Any]:
    """Activity to update inventory status"""
    try:
        # This would update inventory metadata/status in your database
        db = get_db()
        
        result = db.products.update_one(
            {"product_id": status_data["product_id"]},
            {
                "$set": {
                    "workflow_status": status_data["status"],
                    "last_workflow_update": datetime.utcnow()
                }
            }
        )
        
        return {"status": "success", "updated": result.modified_count > 0}
        
    except Exception as e:
        logger.error("Failed to update inventory status", error=str(e))
        return {"status": "error", "message": str(e)}

@activity.defn
async def calculate_demand_forecast(product_id: str) -> Dict[str, Any]:
    """Activity to calculate demand forecast using AI"""
    try:
        result = await ai_forecasting_service.forecast_demand_ai(product_id, days_ahead=30)
        return result
        
    except Exception as e:
        logger.error("Failed to calculate demand forecast", product_id=product_id, error=str(e))
        return {"status": "error", "message": str(e)}

# Global instance
temporal_service = TemporalInventoryService() 
"""
Unit tests for Real-time Alerting Service
Tests WebSocket alerts, alert lifecycle, and background processing
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from dataclasses import asdict

from backend.services.real_time_alerting_service import (
    RealTimeAlertingService,
    Alert,
    AlertSeverity,
    AlertStatus,
    AlertType,
    NotificationChannel,
    real_time_alerting_service
)


class TestRealTimeAlertingService:
    """Test suite for Real-time Alerting Service"""
    
    @pytest.fixture
    def service(self):
        """Create a fresh alerting service instance"""
        return RealTimeAlertingService()
    
    @pytest.fixture
    def mock_alert(self):
        """Mock alert data"""
        return Alert(
            alert_id="alert_001",
            alert_type=AlertType.LOW_STOCK,
            product_id="PROD001",
            title="Low Stock Alert",
            message="Product PROD001 is running low",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_service_initialization(self, service):
        """Test service initializes correctly"""
        assert isinstance(service.active_connections, set)
        assert isinstance(service.alert_rules, list)
        assert isinstance(service.notification_channels, list)
        assert isinstance(service.alert_cache, dict)
        assert service.running is False

    @pytest.mark.asyncio
    async def test_initialize_service(self, service):
        """Test service initialization"""
        with patch.object(service, '_load_alert_rules') as mock_load_rules, \
             patch.object(service, '_load_notification_channels') as mock_load_channels, \
             patch('asyncio.create_task') as mock_create_task:
            
            result = await service.initialize()
            
            assert result is True
            assert service.running is True
            mock_load_rules.assert_called_once()
            mock_load_channels.assert_called_once()
            assert mock_create_task.call_count == 2  # Two background tasks

    @pytest.mark.asyncio
    async def test_stop_service(self, service):
        """Test service stopping"""
        service.running = True
        await service.stop()
        assert service.running is False

    # WebSocket Connection Management Tests

    @pytest.mark.asyncio
    async def test_add_websocket_connection(self, service):
        """Test adding WebSocket connection"""
        mock_websocket = Mock()
        
        await service.add_websocket_connection(mock_websocket)
        
        assert mock_websocket in service.active_connections
        assert len(service.active_connections) == 1

    @pytest.mark.asyncio
    async def test_remove_websocket_connection(self, service):
        """Test removing WebSocket connection"""
        mock_websocket = Mock()
        service.active_connections.add(mock_websocket)
        
        await service.remove_websocket_connection(mock_websocket)
        
        assert mock_websocket not in service.active_connections
        assert len(service.active_connections) == 0

    @pytest.mark.asyncio
    async def test_broadcast_alert_no_connections(self, service, mock_alert):
        """Test broadcasting with no active connections"""
        # Should not raise an exception
        await service.broadcast_alert(mock_alert)
        assert True  # Test passes if no exception

    @pytest.mark.asyncio
    async def test_broadcast_alert_with_connections(self, service, mock_alert):
        """Test broadcasting alert to connected clients"""
        mock_websocket1 = AsyncMock()
        mock_websocket2 = AsyncMock()
        
        service.active_connections.add(mock_websocket1)
        service.active_connections.add(mock_websocket2)
        
        await service.broadcast_alert(mock_alert)
        
        # Both websockets should have received the message
        mock_websocket1.send.assert_called_once()
        mock_websocket2.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_broadcast_alert_connection_failure(self, service, mock_alert):
        """Test broadcasting with failed connection"""
        mock_websocket_good = AsyncMock()
        mock_websocket_bad = AsyncMock()
        mock_websocket_bad.send.side_effect = Exception("Connection lost")
        
        service.active_connections.add(mock_websocket_good)
        service.active_connections.add(mock_websocket_bad)
        
        await service.broadcast_alert(mock_alert)
        
        # Good connection should still work, bad one should be removed
        mock_websocket_good.send.assert_called_once()
        assert mock_websocket_bad not in service.active_connections
        assert mock_websocket_good in service.active_connections

    # Alert Management Tests

    @patch('backend.services.real_time_alerting_service.get_db')
    @pytest.mark.asyncio
    async def test_create_alert(self, mock_db, service):
        """Test alert creation"""
        mock_db.return_value.alerts.insert_one = Mock()
        
        with patch.object(service, 'broadcast_alert') as mock_broadcast, \
             patch.object(service, '_send_notifications') as mock_notify:
            
            result = await service.create_alert(
                alert_type=AlertType.LOW_STOCK,
                title="Test Alert",
                message="Test message",
                severity=AlertSeverity.HIGH,
                product_id="PROD001"
            )
            
            assert isinstance(result, Alert)
            assert result.alert_type == AlertType.LOW_STOCK
            assert result.severity == AlertSeverity.HIGH
            assert result.status == AlertStatus.ACTIVE
            assert result.product_id == "PROD001"
            
            # Should be in cache
            assert result.alert_id in service.alert_cache
            
            # Should have broadcast and sent notifications
            mock_broadcast.assert_called_once_with(result)
            mock_notify.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, service, mock_alert):
        """Test successful alert acknowledgment"""
        service.alert_cache[mock_alert.alert_id] = mock_alert
        
        with patch.object(service, '_update_alert_in_db') as mock_update, \
             patch.object(service, 'broadcast_alert') as mock_broadcast:
            
            result = await service.acknowledge_alert(mock_alert.alert_id, "user1")
            
            assert result is True
            assert mock_alert.status == AlertStatus.ACKNOWLEDGED
            assert mock_alert.acknowledged_by == "user1"
            mock_update.assert_called_once_with(mock_alert)
            mock_broadcast.assert_called_once_with(mock_alert)

    @pytest.mark.asyncio
    async def test_acknowledge_alert_not_found(self, service):
        """Test acknowledging non-existent alert"""
        result = await service.acknowledge_alert("nonexistent", "user1")
        assert result is False

    @pytest.mark.asyncio
    async def test_resolve_alert_success(self, service, mock_alert):
        """Test successful alert resolution"""
        service.alert_cache[mock_alert.alert_id] = mock_alert
        
        with patch.object(service, '_update_alert_in_db') as mock_update, \
             patch.object(service, 'broadcast_alert') as mock_broadcast:
            
            result = await service.resolve_alert(mock_alert.alert_id, "user1", "Issue fixed")
            
            assert result is True
            assert mock_alert.status == AlertStatus.RESOLVED
            assert mock_alert.resolved_by == "user1"
            assert mock_alert.resolved_at is not None
            assert mock_alert.metadata["resolution_note"] == "Issue fixed"
            mock_update.assert_called_once_with(mock_alert)
            mock_broadcast.assert_called_once_with(mock_alert)

    def test_get_active_alerts_all(self, service, mock_alert):
        """Test getting all active alerts"""
        active_alert = mock_alert
        resolved_alert = Alert(
            alert_id="alert_002",
            alert_type=AlertType.STOCK_OUT,
            product_id="PROD002",
            title="Resolved Alert",
            message="This was resolved",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.RESOLVED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        service.alert_cache[active_alert.alert_id] = active_alert
        service.alert_cache[resolved_alert.alert_id] = resolved_alert
        
        result = asyncio.run(service.get_active_alerts())
        
        assert len(result) == 1
        assert result[0].alert_id == active_alert.alert_id

    def test_get_active_alerts_filtered(self, service, mock_alert):
        """Test getting active alerts filtered by product"""
        alert1 = mock_alert
        alert2 = Alert(
            alert_id="alert_002",
            alert_type=AlertType.STOCK_OUT,
            product_id="PROD002",
            title="Other Alert",
            message="Different product",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        service.alert_cache[alert1.alert_id] = alert1
        service.alert_cache[alert2.alert_id] = alert2
        
        result = asyncio.run(service.get_active_alerts(product_id="PROD001"))
        
        assert len(result) == 1
        assert result[0].product_id == "PROD001"

    # Smart Alert Generation Tests

    @patch('backend.services.real_time_alerting_service.get_db')
    @pytest.mark.asyncio
    async def test_check_and_create_low_stock_alerts(self, mock_db, service):
        """Test low stock alert generation"""
        # Mock database response
        mock_db.return_value.products.aggregate.return_value = [
            {
                "product_id": "PROD001",
                "current_stock": 5,
                "reorder_point": 10,
                "stock_percentage": 10.0,
                "name": "Test Product"
            }
        ]
        
        with patch.object(service, 'create_alert') as mock_create:
            await service.check_and_create_low_stock_alerts()
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['alert_type'] == AlertType.LOW_STOCK
            assert call_args[1]['product_id'] == "PROD001"

    @patch('backend.services.real_time_alerting_service.get_db')
    @patch('backend.services.real_time_alerting_service.ai_forecasting_service')
    @pytest.mark.asyncio
    async def test_check_and_create_anomaly_alerts(self, mock_ai, mock_db, service):
        """Test anomaly detection alert generation"""
        # Mock database and AI responses
        mock_db.return_value.products.find.return_value.limit.return_value = [
            {
                "product_id": "PROD001",
                "current_stock": 100,
                "name": "Test Product"
            }
        ]
        
        mock_ai.forecast_demand_ai.return_value = {
            "status": "success",
            "ai_forecast": {
                "forecast": {
                    "total_demand": 250,  # High demand
                    "insights": ["Demand spike detected"]
                }
            }
        }
        
        with patch.object(service, 'create_alert') as mock_create:
            await service.check_and_create_anomaly_alerts()
            
            mock_create.assert_called_once()
            call_args = mock_create.call_args
            assert call_args[1]['alert_type'] == AlertType.DEMAND_SPIKE

    # Background Processing Tests

    @pytest.mark.asyncio
    async def test_process_alerts_continuously(self, service):
        """Test continuous alert processing"""
        service.running = True
        
        with patch.object(service, 'check_and_create_low_stock_alerts') as mock_low_stock, \
             patch.object(service, 'check_and_create_anomaly_alerts') as mock_anomaly, \
             patch.object(service, '_check_alert_escalation') as mock_escalation, \
             patch('asyncio.sleep') as mock_sleep:
            
            # Mock sleep to raise exception and break the loop
            mock_sleep.side_effect = [None, KeyboardInterrupt()]
            
            try:
                await service._process_alerts_continuously()
            except KeyboardInterrupt:
                pass
            
            mock_low_stock.assert_called()
            mock_escalation.assert_called()
            assert mock_sleep.call_count >= 1

    @pytest.mark.asyncio
    async def test_check_alert_escalation(self, service):
        """Test alert escalation logic"""
        # Create an old unacknowledged critical alert
        old_time = datetime.utcnow() - timedelta(hours=3)
        critical_alert = Alert(
            alert_id="alert_critical",
            alert_type=AlertType.STOCK_OUT,
            product_id="PROD001",
            title="Critical Alert",
            message="Critical issue",
            severity=AlertSeverity.CRITICAL,
            status=AlertStatus.ACTIVE,
            created_at=old_time,
            updated_at=old_time
        )
        
        service.alert_cache[critical_alert.alert_id] = critical_alert
        
        with patch.object(service, '_update_alert_in_db') as mock_update, \
             patch.object(service, 'broadcast_alert') as mock_broadcast, \
             patch.object(service, '_send_escalation_notification') as mock_escalate:
            
            await service._check_alert_escalation()
            
            assert critical_alert.status == AlertStatus.ESCALATED
            mock_update.assert_called_once_with(critical_alert)
            mock_broadcast.assert_called_once_with(critical_alert)
            mock_escalate.assert_called_once_with(critical_alert)

    @pytest.mark.asyncio
    async def test_cleanup_old_alerts(self, service):
        """Test cleanup of old resolved alerts"""
        # Create old resolved alert
        old_time = datetime.utcnow() - timedelta(days=35)
        old_alert = Alert(
            alert_id="alert_old",
            alert_type=AlertType.LOW_STOCK,
            product_id="PROD001",
            title="Old Alert",
            message="Old resolved alert",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.RESOLVED,
            created_at=old_time,
            updated_at=old_time,
            resolved_at=old_time
        )
        
        # Create recent resolved alert
        recent_time = datetime.utcnow() - timedelta(days=5)
        recent_alert = Alert(
            alert_id="alert_recent",
            alert_type=AlertType.LOW_STOCK,
            product_id="PROD002",
            title="Recent Alert",
            message="Recent resolved alert",
            severity=AlertSeverity.MEDIUM,
            status=AlertStatus.RESOLVED,
            created_at=recent_time,
            updated_at=recent_time,
            resolved_at=recent_time
        )
        
        service.alert_cache[old_alert.alert_id] = old_alert
        service.alert_cache[recent_alert.alert_id] = recent_alert
        service.running = True
        
        with patch('asyncio.sleep') as mock_sleep:
            mock_sleep.side_effect = [KeyboardInterrupt()]
            
            try:
                await service._cleanup_old_alerts()
            except KeyboardInterrupt:
                pass
            
            # Old alert should be removed, recent one should remain
            assert old_alert.alert_id not in service.alert_cache
            assert recent_alert.alert_id in service.alert_cache

    # Database Operations Tests

    @patch('backend.services.real_time_alerting_service.get_db')
    @pytest.mark.asyncio
    async def test_store_alert_to_db(self, mock_db, service, mock_alert):
        """Test storing alert to database"""
        mock_db.return_value.alerts.insert_one = Mock()
        
        await service._store_alert_to_db(mock_alert)
        
        mock_db.return_value.alerts.insert_one.assert_called_once()
        call_args = mock_db.return_value.alerts.insert_one.call_args[0][0]
        assert call_args['alert_id'] == mock_alert.alert_id
        assert call_args['alert_type'] == mock_alert.alert_type.value

    @patch('backend.services.real_time_alerting_service.get_db')
    @pytest.mark.asyncio
    async def test_update_alert_in_db(self, mock_db, service, mock_alert):
        """Test updating alert in database"""
        mock_db.return_value.alerts.update_one = Mock()
        
        await service._update_alert_in_db(mock_alert)
        
        mock_db.return_value.alerts.update_one.assert_called_once()

    # Notification System Tests

    @pytest.mark.asyncio
    async def test_send_notifications(self, service, mock_alert):
        """Test sending notifications"""
        email_channel = NotificationChannel(
            channel_type="email",
            endpoint="test@example.com",
            enabled=True,
            severity_filter=[AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        )
        
        webhook_channel = NotificationChannel(
            channel_type="webhook",
            endpoint="http://example.com/webhook",
            enabled=True
        )
        
        service.notification_channels = [email_channel, webhook_channel]
        
        with patch.object(service, '_send_email_notification') as mock_email, \
             patch.object(service, '_send_webhook_notification') as mock_webhook:
            
            await service._send_notifications(mock_alert)
            
            mock_email.assert_called_once()
            mock_webhook.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notifications_severity_filter(self, service):
        """Test notification filtering by severity"""
        low_alert = Alert(
            alert_id="alert_low",
            alert_type=AlertType.LOW_STOCK,
            product_id="PROD001",
            title="Low Severity Alert",
            message="Low severity message",
            severity=AlertSeverity.LOW,
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        high_only_channel = NotificationChannel(
            channel_type="email",
            endpoint="test@example.com",
            enabled=True,
            severity_filter=[AlertSeverity.HIGH, AlertSeverity.CRITICAL]
        )
        
        service.notification_channels = [high_only_channel]
        
        with patch.object(service, '_send_email_notification') as mock_email:
            await service._send_notifications(low_alert)
            
            # Should not send notification due to severity filter
            mock_email.assert_not_called()

    def test_load_alert_rules(self, service):
        """Test loading alert rules"""
        asyncio.run(service._load_alert_rules())
        
        assert len(service.alert_rules) > 0
        assert service.alert_rules[0]['name'] == 'low_stock_threshold'

    def test_load_notification_channels(self, service):
        """Test loading notification channels"""
        asyncio.run(service._load_notification_channels())
        
        assert len(service.notification_channels) > 0
        assert service.notification_channels[0].channel_type == 'webhook'


# Integration Tests
class TestRealTimeAlertingServiceIntegration:
    """Integration tests for Real-time Alerting Service"""
    
    @pytest.mark.asyncio
    async def test_global_service_instance(self):
        """Test that global service instance works"""
        assert real_time_alerting_service is not None
        assert isinstance(real_time_alerting_service, RealTimeAlertingService)

    def test_alert_dataclass(self):
        """Test Alert dataclass functionality"""
        alert = Alert(
            alert_id="test_001",
            alert_type=AlertType.LOW_STOCK,
            product_id="PROD001",
            title="Test Alert",
            message="Test message",
            severity=AlertSeverity.HIGH,
            status=AlertStatus.ACTIVE,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Test serialization
        alert_dict = asdict(alert)
        assert alert_dict['alert_id'] == "test_001"
        assert alert_dict['alert_type'] == AlertType.LOW_STOCK
        
        # Test enum values
        assert alert.severity == AlertSeverity.HIGH
        assert alert.status == AlertStatus.ACTIVE

    def test_notification_channel_dataclass(self):
        """Test NotificationChannel dataclass"""
        channel = NotificationChannel(
            channel_type="email",
            endpoint="test@example.com",
            enabled=True,
            severity_filter=[AlertSeverity.HIGH]
        )
        
        assert channel.channel_type == "email"
        assert channel.enabled is True
        assert AlertSeverity.HIGH in channel.severity_filter

    def test_alert_enums(self):
        """Test alert enumeration values"""
        # Test AlertSeverity
        assert AlertSeverity.LOW.value == "low"
        assert AlertSeverity.CRITICAL.value == "critical"
        
        # Test AlertStatus
        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.RESOLVED.value == "resolved"
        
        # Test AlertType
        assert AlertType.LOW_STOCK.value == "low_stock"
        assert AlertType.DEMAND_SPIKE.value == "demand_spike"

    @pytest.mark.asyncio
    async def test_end_to_end_alert_lifecycle(self):
        """Test complete alert lifecycle"""
        service = RealTimeAlertingService()
        
        # Initialize service
        with patch.object(service, '_load_alert_rules'), \
             patch.object(service, '_load_notification_channels'), \
             patch('asyncio.create_task'):
            await service.initialize()
        
        # Create alert
        with patch('backend.services.real_time_alerting_service.get_db'), \
             patch.object(service, 'broadcast_alert'), \
             patch.object(service, '_send_notifications'):
            
            alert = await service.create_alert(
                alert_type=AlertType.LOW_STOCK,
                title="Test Alert",
                message="Test message",
                severity=AlertSeverity.HIGH,
                product_id="PROD001"
            )
            
            assert alert.status == AlertStatus.ACTIVE
        
        # Acknowledge alert
        with patch.object(service, '_update_alert_in_db'), \
             patch.object(service, 'broadcast_alert'):
            
            result = await service.acknowledge_alert(alert.alert_id, "user1")
            assert result is True
            assert alert.status == AlertStatus.ACKNOWLEDGED
        
        # Resolve alert
        with patch.object(service, '_update_alert_in_db'), \
             patch.object(service, 'broadcast_alert'):
            
            result = await service.resolve_alert(alert.alert_id, "user1", "Fixed")
            assert result is True
            assert alert.status == AlertStatus.RESOLVED


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 
"""
Alert routes for inventory alerts and notifications
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
from datetime import datetime
import structlog

from backend.models.alert_model import Alert
from backend.services.db_service import get_db

logger = structlog.get_logger()

alerts_ns = Namespace('alerts', description='Alert management endpoints')

# API Models for documentation
alert_model = alerts_ns.model('Alert', {
    'alert_id': fields.String(description='Alert ID'),
    'type': fields.String(required=True, description='Alert type (low_stock, overstock, expiring, price_change, delivery_delay)'),
    'severity': fields.String(description='Alert severity (low, medium, high, critical)'),
    'title': fields.String(required=True, description='Alert title'),
    'message': fields.String(required=True, description='Alert message'),
    'status': fields.String(description='Alert status (active, acknowledged, resolved, dismissed)'),
    'product_id': fields.String(description='Related product ID'),
    'supplier_id': fields.String(description='Related supplier ID'),
    'order_id': fields.String(description='Related order ID'),
    'threshold_value': fields.Float(description='Threshold value that triggered the alert'),
    'current_value': fields.Float(description='Current value'),
    'category': fields.String(description='Alert category'),
    'action_required': fields.Boolean(description='Whether action is required'),
    'tags': fields.List(fields.String, description='Alert tags'),
    'metadata': fields.Raw(description='Additional metadata')
})

@alerts_ns.route('/')
class AlertList(Resource):
    """Alert list endpoint"""
    
    @alerts_ns.doc('list_alerts')
    def get(self):
        """Get all alerts with optional filtering"""
        try:
            db = get_db()
            collection = db.alerts
            
            # Get query parameters
            status = request.args.get('status', 'active')
            severity = request.args.get('severity')
            alert_type = request.args.get('type')
            product_id = request.args.get('product_id')
            supplier_id = request.args.get('supplier_id')
            action_required = request.args.get('action_required', type=bool)
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Build filter
            filter_query = {}
            if status:
                filter_query['status'] = status
            if severity:
                filter_query['severity'] = severity
            if alert_type:
                filter_query['type'] = alert_type
            if product_id:
                filter_query['product_id'] = product_id
            if supplier_id:
                filter_query['supplier_id'] = supplier_id
            if action_required is not None:
                filter_query['action_required'] = action_required
            
            # Execute query with pagination
            skip = (page - 1) * per_page
            cursor = collection.find(filter_query).sort('created_at', -1).skip(skip).limit(per_page)
            alerts = []
            
            for alert_doc in cursor:
                alert = Alert().from_dict(alert_doc)
                alerts.append(alert.to_dict())
            
            # Get total count
            total_count = collection.count_documents(filter_query)
            
            # Get summary statistics
            stats = {
                'total': total_count,
                'by_severity': {},
                'by_status': {},
                'action_required': collection.count_documents({**filter_query, 'action_required': True})
            }
            
            # Count by severity
            for severity_level in ['low', 'medium', 'high', 'critical']:
                count = collection.count_documents({**filter_query, 'severity': severity_level})
                stats['by_severity'][severity_level] = count
            
            # Count by status
            for status_level in ['active', 'acknowledged', 'resolved', 'dismissed']:
                count = collection.count_documents({**filter_query, 'status': status_level})
                stats['by_status'][status_level] = count
            
            return {
                'alerts': alerts,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'statistics': stats,
                'message': f'Retrieved {len(alerts)} alerts',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching alerts", error=str(e))
            return {'error': 'Failed to fetch alerts', 'status': 'error'}, 500
    
    @alerts_ns.doc('create_alert')
    @alerts_ns.expect(alert_model)
    def post(self):
        """Create new alert"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
                
            # Create alert instance
            alert = Alert()
            alert.from_dict(data)
            
            # Validate required fields
            if not alert.validate():
                return {'error': 'Missing required fields or invalid data', 'status': 'error'}, 400
            
            # Save to database
            db = get_db()
            alert.before_save()
            alerts_collection = db.alerts
            alert_dict = alert.to_dict()
            result = alerts_collection.insert_one(alert_dict)
            
            # Return created alert
            created_alert = alerts_collection.find_one({'_id': result.inserted_id})
            response_alert = Alert().from_dict(created_alert)
            
            return {
                'alert': response_alert.to_dict(),
                'message': 'Alert created successfully',
                'status': 'success'
            }, 201
            
        except Exception as e:
            logger.error("Error creating alert", error=str(e))
            return {'error': 'Failed to create alert', 'status': 'error'}, 500


@alerts_ns.route('/<string:alert_id>')
@alerts_ns.param('alert_id', 'Alert identifier')
class AlertDetail(Resource):
    """Single alert operations"""
    
    @alerts_ns.doc('get_alert')
    def get(self, alert_id):
        """Get alert by ID"""
        try:
            db = get_db()
            collection = db.alerts
            
            # Find by alert_id or _id
            query = {'alert_id': alert_id}
            if ObjectId.is_valid(alert_id):
                query = {'$or': [{'alert_id': alert_id}, {'_id': ObjectId(alert_id)}]}
            
            alert_doc = collection.find_one(query)
            if not alert_doc:
                return {'error': 'Alert not found', 'status': 'error'}, 404
            
            alert = Alert().from_dict(alert_doc)
            return {
                'alert': alert.to_dict(),
                'message': 'Alert retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching alert", error=str(e), alert_id=alert_id)
            return {'error': 'Failed to fetch alert', 'status': 'error'}, 500
    
    @alerts_ns.doc('update_alert')
    @alerts_ns.expect(alert_model)
    def put(self, alert_id):
        """Update alert"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.alerts
            
            # Find existing alert
            query = {'alert_id': alert_id}
            if ObjectId.is_valid(alert_id):
                query = {'$or': [{'alert_id': alert_id}, {'_id': ObjectId(alert_id)}]}
            
            existing_alert = collection.find_one(query)
            if not existing_alert:
                return {'error': 'Alert not found', 'status': 'error'}, 404
            
            # Update alert
            alert = Alert().from_dict(existing_alert)
            
            # Update fields from request data
            for key, value in data.items():
                if hasattr(alert, key) and key not in ['_id', 'created_at', 'alert_id']:
                    setattr(alert, key, value)
            
            # Validate and save
            if not alert.validate():
                return {'error': 'Invalid alert data', 'status': 'error'}, 400
            
            alert.before_save()
            alert_dict = alert.to_dict()
            
            # Remove _id for update
            if '_id' in alert_dict:
                del alert_dict['_id']
            
            collection.update_one(query, {'$set': alert_dict})
            
            # Return updated alert
            updated_alert = collection.find_one(query)
            response_alert = Alert().from_dict(updated_alert)
            
            return {
                'alert': response_alert.to_dict(),
                'message': 'Alert updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating alert", error=str(e), alert_id=alert_id)
            return {'error': 'Failed to update alert', 'status': 'error'}, 500
    
    @alerts_ns.doc('delete_alert')
    def delete(self, alert_id):
        """Delete alert"""
        try:
            db = get_db()
            collection = db.alerts
            
            # Find by alert_id or _id
            query = {'alert_id': alert_id}
            if ObjectId.is_valid(alert_id):
                query = {'$or': [{'alert_id': alert_id}, {'_id': ObjectId(alert_id)}]}
            
            result = collection.delete_one(query)
            if result.deleted_count == 0:
                return {'error': 'Alert not found', 'status': 'error'}, 404
            
            return {
                'message': 'Alert deleted successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error deleting alert", error=str(e), alert_id=alert_id)
            return {'error': 'Failed to delete alert', 'status': 'error'}, 500


@alerts_ns.route('/<string:alert_id>/acknowledge')
@alerts_ns.param('alert_id', 'Alert identifier')
class AlertAcknowledge(Resource):
    """Acknowledge alert"""
    
    @alerts_ns.doc('acknowledge_alert')
    def put(self, alert_id):
        """Acknowledge an alert"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'system')
            
            db = get_db()
            collection = db.alerts
            
            # Find alert
            query = {'alert_id': alert_id}
            if ObjectId.is_valid(alert_id):
                query = {'$or': [{'alert_id': alert_id}, {'_id': ObjectId(alert_id)}]}
            
            existing_alert = collection.find_one(query)
            if not existing_alert:
                return {'error': 'Alert not found', 'status': 'error'}, 404
            
            # Update to acknowledged
            alert = Alert().from_dict(existing_alert)
            alert.acknowledge(user_id)
            
            alert_dict = alert.to_dict()
            if '_id' in alert_dict:
                del alert_dict['_id']
            
            collection.update_one(query, {'$set': alert_dict})
            
            # Return updated alert
            updated_alert = collection.find_one(query)
            response_alert = Alert().from_dict(updated_alert)
            
            return {
                'alert': response_alert.to_dict(),
                'message': 'Alert acknowledged successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error acknowledging alert", error=str(e), alert_id=alert_id)
            return {'error': 'Failed to acknowledge alert', 'status': 'error'}, 500


@alerts_ns.route('/<string:alert_id>/resolve')
@alerts_ns.param('alert_id', 'Alert identifier')
class AlertResolve(Resource):
    """Resolve alert"""
    
    @alerts_ns.doc('resolve_alert')
    def put(self, alert_id):
        """Resolve an alert"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'system')
            
            db = get_db()
            collection = db.alerts
            
            # Find alert
            query = {'alert_id': alert_id}
            if ObjectId.is_valid(alert_id):
                query = {'$or': [{'alert_id': alert_id}, {'_id': ObjectId(alert_id)}]}
            
            existing_alert = collection.find_one(query)
            if not existing_alert:
                return {'error': 'Alert not found', 'status': 'error'}, 404
            
            # Update to resolved
            alert = Alert().from_dict(existing_alert)
            alert.resolve(user_id)
            
            alert_dict = alert.to_dict()
            if '_id' in alert_dict:
                del alert_dict['_id']
            
            collection.update_one(query, {'$set': alert_dict})
            
            # Return updated alert
            updated_alert = collection.find_one(query)
            response_alert = Alert().from_dict(updated_alert)
            
            return {
                'alert': response_alert.to_dict(),
                'message': 'Alert resolved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error resolving alert", error=str(e), alert_id=alert_id)
            return {'error': 'Failed to resolve alert', 'status': 'error'}, 500


@alerts_ns.route('/severity/<string:severity>')
@alerts_ns.param('severity', 'Alert severity (low, medium, high, critical)')
class AlertsBySeverity(Resource):
    """Alerts filtered by severity"""
    
    @alerts_ns.doc('get_alerts_by_severity')
    def get(self, severity):
        """Get alerts by severity level"""
        try:
            db = get_db()
            collection = db.alerts
            
            # Validate severity
            valid_severities = ['low', 'medium', 'high', 'critical']
            if severity not in valid_severities:
                return {'error': f'Invalid severity. Must be one of: {valid_severities}', 'status': 'error'}, 400
            
            # Find alerts with specified severity
            cursor = collection.find({'severity': severity}).sort('created_at', -1)
            alerts = []
            
            for alert_doc in cursor:
                alert = Alert().from_dict(alert_doc)
                alerts.append(alert.to_dict())
            
            return {
                'alerts': alerts,
                'severity_filter': severity,
                'count': len(alerts),
                'message': f'Retrieved {len(alerts)} alerts with severity: {severity}',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching alerts by severity", error=str(e), severity=severity)
            return {'error': 'Failed to fetch alerts by severity', 'status': 'error'}, 500


@alerts_ns.route('/summary')
class AlertSummary(Resource):
    """Alert summary statistics"""
    
    @alerts_ns.doc('get_alert_summary')
    def get(self):
        """Get alert summary and statistics"""
        try:
            db = get_db()
            collection = db.alerts
            
            # Get counts by status
            active_count = collection.count_documents({'status': 'active'})
            acknowledged_count = collection.count_documents({'status': 'acknowledged'})
            resolved_count = collection.count_documents({'status': 'resolved'})
            dismissed_count = collection.count_documents({'status': 'dismissed'})
            
            # Get counts by severity
            critical_count = collection.count_documents({'severity': 'critical', 'status': 'active'})
            high_count = collection.count_documents({'severity': 'high', 'status': 'active'})
            medium_count = collection.count_documents({'severity': 'medium', 'status': 'active'})
            low_count = collection.count_documents({'severity': 'low', 'status': 'active'})
            
            # Get counts by type
            type_counts = {}
            pipeline = [
                {'$match': {'status': 'active'}},
                {'$group': {'_id': '$type', 'count': {'$sum': 1}}}
            ]
            for result in collection.aggregate(pipeline):
                type_counts[result['_id']] = result['count']
            
            # Get action required count
            action_required_count = collection.count_documents({'action_required': True, 'status': 'active'})
            
            # Get recent alerts (last 24 hours)
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_count = collection.count_documents({
                'created_at': {'$gte': yesterday.isoformat()},
                'status': 'active'
            })
            
            summary = {
                'status_counts': {
                    'active': active_count,
                    'acknowledged': acknowledged_count,
                    'resolved': resolved_count,
                    'dismissed': dismissed_count
                },
                'severity_counts': {
                    'critical': critical_count,
                    'high': high_count,
                    'medium': medium_count,
                    'low': low_count
                },
                'type_counts': type_counts,
                'action_required': action_required_count,
                'recent_24h': recent_count,
                'total_active': active_count
            }
            
            return {
                'summary': summary,
                'message': 'Alert summary retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching alert summary", error=str(e))
            return {'error': 'Failed to fetch alert summary', 'status': 'error'}, 500 
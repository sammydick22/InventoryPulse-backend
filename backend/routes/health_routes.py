"""
Health and system status routes
"""
from flask import current_app
from flask_restx import Namespace, Resource
import structlog
from datetime import datetime

import backend.services.db_service as db_service
import backend.services.snowflake_service as snowflake_service

logger = structlog.get_logger()

system_ns = Namespace('system', description='System health and status endpoints')


@system_ns.route('/health')
class HealthCheck(Resource):
    """System health check endpoint"""
    
    def get(self):
        """
        Get system health status
        Returns overall health status and dependency checks
        """
        try:
            health_status = {
                'status': 'ok',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'version': '1.0.0',
                'environment': current_app.config.get('FLASK_ENV', 'unknown'),
                'dependencies': {}
            }
            
            # Check MongoDB connection
            try:
                db = db_service.get_db()
                db.command('ping')
                health_status['dependencies']['mongodb'] = 'connected'
            except Exception as e:
                health_status['dependencies']['mongodb'] = f'error: {str(e)}'
                health_status['status'] = 'degraded'
            
            # Redis not needed for hackathon project
            
            # Check Temporal connection (basic check)
            temporal_endpoint = current_app.config.get('TEMPORAL_GRPC_ENDPOINT')
            if temporal_endpoint:
                health_status['dependencies']['temporal'] = 'configured'
            else:
                health_status['dependencies']['temporal'] = 'not_configured'
            
            # Check external services configuration
            minimax_key = current_app.config.get('MINIMAX_API_KEY')
            health_status['dependencies']['minimax'] = 'configured' if minimax_key else 'not_configured'
            
            # Check Snowflake connection
            try:
                conn = snowflake_service.get_snowflake_connection()
                if conn:
                    with conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    health_status['dependencies']['snowflake'] = 'connected'
                else:
                    health_status['dependencies']['snowflake'] = 'error: connection failed'
                    health_status['status'] = 'degraded'
            except Exception as e:
                health_status['dependencies']['snowflake'] = f'error: {str(e)}'
                health_status['status'] = 'degraded'
            
            status_code = 200 if health_status['status'] == 'ok' else 503
            
            logger.info("Health check performed", 
                       status=health_status['status'],
                       dependencies=health_status['dependencies'])
            
            return health_status, status_code
            
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                'status': 'error',
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'error': str(e)
            }, 500


@system_ns.route('/stats')
class SystemStats(Resource):
    """System statistics endpoint"""
    
    def get(self):
        """
        Get system statistics
        Returns database collection counts and other metrics
        """
        try:
            db = db_service.get_db()
            
            stats = {
                'timestamp': datetime.utcnow().isoformat() + 'Z',
                'database_stats': {},
                'system_info': {
                    'version': '1.0.0',
                    'environment': current_app.config.get('FLASK_ENV', 'unknown')
                }
            }
            
            # Get collection counts
            collections = ['products', 'suppliers', 'purchase_orders', 
                          'stock_movements', 'users', 'alerts']
            
            for collection_name in collections:
                try:
                    count = db[collection_name].count_documents({})
                    stats['database_stats'][collection_name] = count
                except Exception as e:
                    stats['database_stats'][collection_name] = f'error: {str(e)}'
            
            # Get database size info
            try:
                db_stats = db.command('dbstats')
                stats['database_stats']['total_size_mb'] = round(db_stats.get('dataSize', 0) / (1024 * 1024), 2)
                stats['database_stats']['index_size_mb'] = round(db_stats.get('indexSize', 0) / (1024 * 1024), 2)
            except Exception as e:
                logger.warning("Could not get database size stats", error=str(e))
            
            logger.info("System stats retrieved", stats=stats['database_stats'])
            
            return stats, 200
            
        except Exception as e:
            logger.error("Failed to get system stats", error=str(e))
            return {
                'error': 'Failed to retrieve system statistics',
                'message': str(e)
            }, 500 
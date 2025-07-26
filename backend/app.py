"""
InventoryPulse Flask Application
Main application factory and configuration
"""
import os
import structlog
from flask import Flask
from flask_cors import CORS

from flask_restx import Api

from backend.config import config
import backend.services.db_service as db_service
import backend.services.snowflake_service as snowflake_service
from backend.utils.errors import register_error_handlers


def create_app(config_name=None):
    """Application factory pattern"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Initialize extensions
    CORS(app, origins=app.config['CORS_ORIGINS'])
    # Note: JWT removed for hackathon simplicity
    
    # Initialize database (can be patched in tests)
    db_service.init_db(app)
    
    # Initialize Snowflake service
    snowflake_service.init_app(app)

    # Create API instance
    api = Api(
        app,
        version='1.0.0',
        title='InventoryPulse API',
        description='AI-powered inventory management system API',
        doc='/api/docs/',
        prefix='/api'
    )
    
    # Register blueprints/namespaces
    register_blueprints(api)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check route
    @app.route('/health')
    def health_check():
        return {
            'status': 'ok',
            'version': '1.0.0',
            'environment': config_name
        }
    
    return app


def register_blueprints(api):
    """Register all API namespaces"""
    
    # Import blueprints here to avoid circular imports
    from backend.routes.auth_routes import auth_ns
    from backend.routes.product_routes import products_ns
    from backend.routes.supplier_routes import suppliers_ns
    from backend.routes.order_routes import orders_ns
    from backend.routes.user_routes import users_ns
    from backend.routes.alert_routes import alerts_ns
    from backend.routes.health_routes import system_ns
    from backend.routes.ai_routes import ai_ns
    
    # Register namespaces
    api.add_namespace(auth_ns, path='/auth')
    api.add_namespace(products_ns, path='/products')
    api.add_namespace(suppliers_ns, path='/suppliers')
    api.add_namespace(orders_ns, path='/orders')
    api.add_namespace(users_ns, path='/users')
    api.add_namespace(alerts_ns, path='/alerts')
    api.add_namespace(system_ns, path='/system')
    api.add_namespace(ai_ns, path='/ai')


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5500, debug=True) 
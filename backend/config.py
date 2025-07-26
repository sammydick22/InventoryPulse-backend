"""
Configuration settings for InventoryPulse application
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Config:
    """Base configuration"""
    # General settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key'
    FLASK_ENV = os.environ.get('FLASK_ENV') or 'development'
    
    # Note: JWT authentication removed for hackathon simplicity
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS') or "*" # Default to all for dev

    # Database settings
    MONGO_URI = os.environ.get('MONGO_URI') or 'mongodb://localhost:27017/InventoryPulseDB'
    MONGO_DB_NAME = os.environ.get('MONGO_DB_NAME') or 'InventoryPulseDB'

    # For hackathon: simplify SSL connection for tests
    MONGO_TLS_ALLOW_INVALID_CERTIFICATES = os.environ.get('MONGO_TLS_ALLOW_INVALID_CERTIFICATES', 'True').lower() in ('true', '1', 't')

    # Snowflake settings
    SNOWFLAKE_USER = os.environ.get('SNOWFLAKE_USERNAME') or os.environ.get('SNOWFLAKE_USER')
    SNOWFLAKE_PASSWORD = os.environ.get('SNOWFLAKE_PASSWORD')
    SNOWFLAKE_ACCOUNT = os.environ.get('SNOWFLAKE_ACCOUNT')
    SNOWFLAKE_WAREHOUSE = os.environ.get('SNOWFLAKE_WAREHOUSE')
    SNOWFLAKE_DATABASE = os.environ.get('SNOWFLAKE_DATABASE')
    SNOWFLAKE_SCHEMA = os.environ.get('SNOWFLAKE_SCHEMA')

    # Minimax API settings
    MINIMAX_GROUP_ID = os.environ.get('MINIMAX_GROUP_ID')
    MINIMAX_API_KEY = os.environ.get('MINIMAX_API_KEY')
    MINIMAX_MODEL = os.environ.get('MINIMAX_MODEL') or 'MiniMax-Text-01'  # Changed to Text-01 for structured output support
    MINIMAX_BASE_URL = os.environ.get('MINIMAX_BASE_URL') or 'https://api.minimax.io'
    
    # External API keys
    NLX_API_KEY = os.environ.get('NLX_API_KEY')
    WIZ_API_KEY = os.environ.get('WIZ_API_KEY')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    
    # Temporal settings
    TEMPORAL_GRPC_ENDPOINT = os.environ.get('TEMPORAL_GRPC_ENDPOINT') or 'localhost:7233'
    TEMPORAL_NAMESPACE = os.environ.get('TEMPORAL_NAMESPACE') or 'default'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class StagingConfig(Config):
    """Staging configuration"""
    DEBUG = False
    FLASK_ENV = 'staging'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    
    # Override with more secure settings in production
    CORS_ORIGINS = []  # Set specific production origins


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    # Use same Atlas connection as development for hackathon simplicity
    # MONGO_URI and MONGO_DB_NAME will inherit from Config class
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'staging': StagingConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
} 
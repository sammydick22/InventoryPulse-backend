"""
Database service for MongoDB connections and operations
"""
import structlog
import logging
import certifi
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure
from flask import current_app, g

logger = structlog.get_logger()

# Global MongoDB client
mongo_client = None
mongo_db = None


def init_db(app):
    """Initialize database connection"""
    global mongo_client, mongo_db
    
    try:
        mongo_uri = app.config['MONGO_URI']
        db_name = app.config['MONGO_DB_NAME']
        
        # Establish connection and store on app context
        mongo_client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
        mongo_db = mongo_client[db_name]
        
        # Store on app for access in other contexts
        app.mongo_client = mongo_client
        app.mongo_db = mongo_db
        
        # Test the connection
        mongo_client.admin.command('ping')
        
        logger.info("MongoDB connection established", 
                   database=db_name)
        
        # Create indexes if they don't exist (will skip if already exist)
        with app.app_context():
            create_indexes()
        
    except ConnectionFailure as e:
        logger.error("Failed to connect to MongoDB", error=str(e))
        raise


def get_db():
    """Get database instance"""
    if 'db' not in g:
        # Try to get from Flask app context or initialize
        try:
            if hasattr(current_app, '_get_current_object'):
                app = current_app._get_current_object()
                if hasattr(app, 'mongo_db') and app.mongo_db is not None:
                    g.db = app.mongo_db
                else:
                    # Initialize new connection for this request
                    mongo_uri = current_app.config['MONGO_URI']
                    db_name = current_app.config['MONGO_DB_NAME']
                    client = MongoClient(mongo_uri, tlsCAFile=certifi.where())
                    g.db = client[db_name]
        except Exception as e:
            logger.error("Failed to get database connection", error=str(e))
            raise RuntimeError("Database not initialized")
    return g.db


def get_collection(collection_name):
    """Get a specific collection"""
    db = get_db()
    return db[collection_name]


def create_indexes():
    """Create database indexes for optimal performance"""
    # Indexes already exist in Atlas - skipping for hackathon
    logger.info("Skipping index creation - indexes already exist in Atlas")
    return


def close_db():
    """Close database connection"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        logger.info("MongoDB connection closed") 
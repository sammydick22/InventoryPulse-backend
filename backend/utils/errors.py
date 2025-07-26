"""
Error handling utilities and custom exceptions
"""
from flask import jsonify, request
from werkzeug.exceptions import HTTPException
import structlog

logger = structlog.get_logger()


class InventoryPulseError(Exception):
    """Base exception for InventoryPulse application"""
    
    def __init__(self, message: str, status_code: int = 500, payload: dict = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload


class ValidationError(InventoryPulseError):
    """Raised when data validation fails"""
    
    def __init__(self, message: str, payload: dict = None):
        super().__init__(message, 400, payload)


class NotFoundError(InventoryPulseError):
    """Raised when a resource is not found"""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)


class ConflictError(InventoryPulseError):
    """Raised when there's a conflict (e.g., duplicate key)"""
    
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(message, 409)


class UnauthorizedError(InventoryPulseError):
    """Raised when authentication fails"""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, 401)


class ForbiddenError(InventoryPulseError):
    """Raised when access is forbidden"""
    
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, 403)


class ExternalServiceError(InventoryPulseError):
    """Raised when external service call fails"""
    
    def __init__(self, message: str, service_name: str = None):
        super().__init__(f"External service error: {message}", 502)
        self.service_name = service_name


def register_error_handlers(app):
    """Register error handlers with Flask app"""
    
    @app.errorhandler(InventoryPulseError)
    def handle_custom_error(error):
        """Handle custom application errors"""
        logger.error("Application error occurred", 
                    error=error.message,
                    status_code=error.status_code,
                    payload=error.payload,
                    path=request.path,
                    method=request.method)
        
        response = {
            'error': error.message,
            'status_code': error.status_code
        }
        
        if error.payload:
            response.update(error.payload)
        
        return jsonify(response), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error):
        """Handle validation errors"""
        logger.warning("Validation error", 
                      error=error.message,
                      payload=error.payload,
                      path=request.path)
        
        response = {
            'error': 'Validation failed',
            'message': error.message,
            'status_code': 400
        }
        
        if error.payload:
            response['details'] = error.payload
        
        return jsonify(response), 400
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors"""
        logger.info("Resource not found", path=request.path, method=request.method)
        
        return jsonify({
            'error': 'Not Found',
            'message': 'The requested resource was not found',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle internal server errors"""
        logger.error("Internal server error", 
                    error=str(error),
                    path=request.path,
                    method=request.method)
        
        return jsonify({
            'error': 'Internal Server Error',
            'message': 'An unexpected error occurred',
            'status_code': 500
        }), 500
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        """Handle HTTP exceptions"""
        logger.warning("HTTP exception", 
                      status_code=error.code,
                      description=error.description,
                      path=request.path)
        
        return jsonify({
            'error': error.name,
            'message': error.description,
            'status_code': error.code
        }), error.code


def create_error_response(message: str, status_code: int = 400, details: dict = None):
    """Create standardized error response"""
    response = {
        'error': message,
        'status_code': status_code
    }
    
    if details:
        response['details'] = details
    
    return jsonify(response), status_code 
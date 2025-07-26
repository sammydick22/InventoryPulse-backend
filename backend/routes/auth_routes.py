"""
Authentication routes
"""
from flask_restx import Namespace, Resource

auth_ns = Namespace('auth', description='Authentication endpoints')


@auth_ns.route('/login')
class Login(Resource):
    """User login endpoint"""
    
    def post(self):
        """
        Demo login - always succeeds for hackathon
        """
        return {
            'message': 'Demo login - placeholder implementation',
            'status': 'placeholder',
            'user': 'demo_user',
            'note': 'Authentication disabled for hackathon demo'
        }


@auth_ns.route('/status')
class AuthStatus(Resource):
    """Authentication status endpoint"""
    
    def get(self):
        """
        Demo auth status - always authenticated for hackathon
        """
        return {
            'message': 'Demo auth status - placeholder implementation',
            'status': 'placeholder',
            'user': 'demo_user',
            'note': 'Authentication disabled for hackathon demo'
        } 
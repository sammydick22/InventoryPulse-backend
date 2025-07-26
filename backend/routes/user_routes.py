"""
User routes for user management
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
from datetime import datetime
import structlog

from backend.models.user_model import User
from backend.services.db_service import get_db

logger = structlog.get_logger()

users_ns = Namespace('users', description='User management endpoints')

# API Models for documentation
user_model = users_ns.model('User', {
    'user_id': fields.String(description='User ID'),
    'username': fields.String(required=True, description='Username'),
    'email': fields.String(required=True, description='Email address'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'role': fields.String(description='User role (admin, manager, user, viewer)'),
    'phone': fields.String(description='Phone number'),
    'department': fields.String(description='Department'),
    'position': fields.String(description='Position/Job title'),
    'status': fields.String(description='User status (active, inactive, suspended)'),
    'permissions': fields.List(fields.String, description='User permissions'),
    'preferences': fields.Raw(description='User preferences')
})

user_profile_model = users_ns.model('UserProfile', {
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'phone': fields.String(description='Phone number'),
    'department': fields.String(description='Department'),
    'position': fields.String(description='Position'),
    'preferences': fields.Raw(description='User preferences')
})

@users_ns.route('/')
class UserList(Resource):
    """User list endpoint"""
    
    @users_ns.doc('list_users')
    def get(self):
        """Get all users with optional filtering"""
        try:
            db = get_db()
            collection = db.users
            
            # Get query parameters
            role = request.args.get('role')
            status = request.args.get('status', 'active')
            department = request.args.get('department')
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Build filter
            filter_query = {}
            if role:
                filter_query['role'] = role
            if status:
                filter_query['status'] = status
            if department:
                filter_query['department'] = department
            
            # Execute query with pagination
            skip = (page - 1) * per_page
            cursor = collection.find(filter_query).skip(skip).limit(per_page)
            users = []
            
            for user_doc in cursor:
                user = User().from_dict(user_doc)
                user_dict = user.to_dict()
                # Remove sensitive information
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                users.append(user_dict)
            
            # Get total count
            total_count = collection.count_documents(filter_query)
            
            # Get statistics
            stats = {
                'total': total_count,
                'by_role': {},
                'by_status': {}
            }
            
            # Count by role
            for role_level in ['admin', 'manager', 'user', 'viewer']:
                count = collection.count_documents({**filter_query, 'role': role_level})
                stats['by_role'][role_level] = count
            
            # Count by status
            for status_level in ['active', 'inactive', 'suspended']:
                count = collection.count_documents({**filter_query, 'status': status_level})
                stats['by_status'][status_level] = count
            
            return {
                'users': users,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'statistics': stats,
                'message': f'Retrieved {len(users)} users',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching users", error=str(e))
            return {'error': 'Failed to fetch users', 'status': 'error'}, 500
    
    @users_ns.doc('create_user')
    @users_ns.expect(user_model)
    def post(self):
        """Create new user"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
                
            # Create user instance
            user = User()
            user.from_dict(data)
            
            # Validate required fields
            if not user.validate():
                return {'error': 'Missing required fields or invalid data', 'status': 'error'}, 400
            
            # Check if username or email already exists
            db = get_db()
            collection = db.users
            if collection.find_one({'username': user.username}):
                return {'error': 'Username already exists', 'status': 'error'}, 409
            if collection.find_one({'email': user.email}):
                return {'error': 'Email already exists', 'status': 'error'}, 409
            
            # Save to database
            user.before_save()
            user_dict = user.to_dict()
            result = collection.insert_one(user_dict)
            
            # Return created user (without password)
            created_user = collection.find_one({'_id': result.inserted_id})
            response_user = User().from_dict(created_user)
            response_dict = response_user.to_dict()
            if 'password_hash' in response_dict:
                del response_dict['password_hash']
            
            return {
                'user': response_dict,
                'message': 'User created successfully',
                'status': 'success'
            }, 201
            
        except Exception as e:
            logger.error("Error creating user", error=str(e))
            return {'error': 'Failed to create user', 'status': 'error'}, 500


@users_ns.route('/<string:user_id>')
@users_ns.param('user_id', 'User identifier')
class UserDetail(Resource):
    """Single user operations"""
    
    @users_ns.doc('get_user')
    def get(self, user_id):
        """Get user by ID"""
        try:
            db = get_db()
            collection = db.users
            
            # Find by user_id or _id
            query = {'user_id': user_id}
            if ObjectId.is_valid(user_id):
                query = {'$or': [{'user_id': user_id}, {'_id': ObjectId(user_id)}]}
            
            user_doc = collection.find_one(query)
            if not user_doc:
                return {'error': 'User not found', 'status': 'error'}, 404
            
            user = User().from_dict(user_doc)
            user_dict = user.to_dict()
            # Remove sensitive information
            if 'password_hash' in user_dict:
                del user_dict['password_hash']
            
            return {
                'user': user_dict,
                'message': 'User retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching user", error=str(e), user_id=user_id)
            return {'error': 'Failed to fetch user', 'status': 'error'}, 500
    
    @users_ns.doc('update_user')
    @users_ns.expect(user_model)
    def put(self, user_id):
        """Update user"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.users
            
            # Find existing user
            query = {'user_id': user_id}
            if ObjectId.is_valid(user_id):
                query = {'$or': [{'user_id': user_id}, {'_id': ObjectId(user_id)}]}
            
            existing_user = collection.find_one(query)
            if not existing_user:
                return {'error': 'User not found', 'status': 'error'}, 404
            
            # Update user
            user = User().from_dict(existing_user)
            
            # Update fields from request data (excluding sensitive fields)
            excluded_fields = ['_id', 'created_at', 'user_id', 'password_hash']
            for key, value in data.items():
                if hasattr(user, key) and key not in excluded_fields:
                    setattr(user, key, value)
            
            # Check for username/email conflicts if they're being changed
            if 'username' in data and data['username'] != existing_user.get('username'):
                if collection.find_one({'username': data['username'], 'user_id': {'$ne': user_id}}):
                    return {'error': 'Username already exists', 'status': 'error'}, 409
            
            if 'email' in data and data['email'] != existing_user.get('email'):
                if collection.find_one({'email': data['email'], 'user_id': {'$ne': user_id}}):
                    return {'error': 'Email already exists', 'status': 'error'}, 409
            
            # Validate and save
            if not user.validate():
                return {'error': 'Invalid user data', 'status': 'error'}, 400
            
            user.before_save()
            user_dict = user.to_dict()
            
            # Remove _id for update
            if '_id' in user_dict:
                del user_dict['_id']
            
            collection.update_one(query, {'$set': user_dict})
            
            # Return updated user (without password)
            updated_user = collection.find_one(query)
            response_user = User().from_dict(updated_user)
            response_dict = response_user.to_dict()
            if 'password_hash' in response_dict:
                del response_dict['password_hash']
            
            return {
                'user': response_dict,
                'message': 'User updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating user", error=str(e), user_id=user_id)
            return {'error': 'Failed to update user', 'status': 'error'}, 500
    
    @users_ns.doc('delete_user')
    def delete(self, user_id):
        """Delete/Deactivate user"""
        try:
            db = get_db()
            collection = db.users
            
            # Find by user_id or _id
            query = {'user_id': user_id}
            if ObjectId.is_valid(user_id):
                query = {'$or': [{'user_id': user_id}, {'_id': ObjectId(user_id)}]}
            
            existing_user = collection.find_one(query)
            if not existing_user:
                return {'error': 'User not found', 'status': 'error'}, 404
            
            # Instead of deleting, deactivate the user
            collection.update_one(query, {'$set': {
                'status': 'inactive',
                'updated_at': datetime.utcnow().isoformat()
            }})
            
            return {
                'message': 'User deactivated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error deactivating user", error=str(e), user_id=user_id)
            return {'error': 'Failed to deactivate user', 'status': 'error'}, 500


@users_ns.route('/<string:user_id>/profile')
@users_ns.param('user_id', 'User identifier')
class UserProfile(Resource):
    """User profile operations"""
    
    @users_ns.doc('update_user_profile')
    @users_ns.expect(user_profile_model)
    def put(self, user_id):
        """Update user profile (non-sensitive information)"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.users
            
            # Find user
            query = {'user_id': user_id}
            if ObjectId.is_valid(user_id):
                query = {'$or': [{'user_id': user_id}, {'_id': ObjectId(user_id)}]}
            
            existing_user = collection.find_one(query)
            if not existing_user:
                return {'error': 'User not found', 'status': 'error'}, 404
            
            # Update only profile fields
            profile_fields = ['first_name', 'last_name', 'phone', 'department', 'position', 'preferences']
            update_data = {}
            
            for field in profile_fields:
                if field in data:
                    update_data[field] = data[field]
            
            if not update_data:
                return {'error': 'No valid profile fields provided', 'status': 'error'}, 400
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.utcnow().isoformat()
            
            collection.update_one(query, {'$set': update_data})
            
            # Return updated user
            updated_user = collection.find_one(query)
            response_user = User().from_dict(updated_user)
            response_dict = response_user.to_dict()
            if 'password_hash' in response_dict:
                del response_dict['password_hash']
            
            return {
                'user': response_dict,
                'message': 'User profile updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating user profile", error=str(e), user_id=user_id)
            return {'error': 'Failed to update user profile', 'status': 'error'}, 500


@users_ns.route('/role/<string:role>')
@users_ns.param('role', 'User role (admin, manager, user, viewer)')
class UsersByRole(Resource):
    """Users filtered by role"""
    
    @users_ns.doc('get_users_by_role')
    def get(self, role):
        """Get users by role"""
        try:
            db = get_db()
            collection = db.users
            
            # Validate role
            valid_roles = ['admin', 'manager', 'user', 'viewer']
            if role not in valid_roles:
                return {'error': f'Invalid role. Must be one of: {valid_roles}', 'status': 'error'}, 400
            
            # Find users with specified role
            cursor = collection.find({'role': role, 'status': 'active'}).sort('username', 1)
            users = []
            
            for user_doc in cursor:
                user = User().from_dict(user_doc)
                user_dict = user.to_dict()
                # Remove sensitive information
                if 'password_hash' in user_dict:
                    del user_dict['password_hash']
                users.append(user_dict)
            
            return {
                'users': users,
                'role_filter': role,
                'count': len(users),
                'message': f'Retrieved {len(users)} users with role: {role}',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching users by role", error=str(e), role=role)
            return {'error': 'Failed to fetch users by role', 'status': 'error'}, 500


@users_ns.route('/<string:user_id>/permissions')
@users_ns.param('user_id', 'User identifier')
class UserPermissions(Resource):
    """User permissions management"""
    
    @users_ns.doc('update_user_permissions')
    def put(self, user_id):
        """Update user permissions"""
        try:
            data = request.get_json()
            if not data or 'permissions' not in data:
                return {'error': 'Permissions list is required', 'status': 'error'}, 400
            
            permissions = data['permissions']
            if not isinstance(permissions, list):
                return {'error': 'Permissions must be a list', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.users
            
            # Find user
            query = {'user_id': user_id}
            if ObjectId.is_valid(user_id):
                query = {'$or': [{'user_id': user_id}, {'_id': ObjectId(user_id)}]}
            
            existing_user = collection.find_one(query)
            if not existing_user:
                return {'error': 'User not found', 'status': 'error'}, 404
            
            # Update permissions
            collection.update_one(query, {'$set': {
                'permissions': permissions,
                'updated_at': datetime.utcnow().isoformat()
            }})
            
            # Return updated user
            updated_user = collection.find_one(query)
            response_user = User().from_dict(updated_user)
            response_dict = response_user.to_dict()
            if 'password_hash' in response_dict:
                del response_dict['password_hash']
            
            return {
                'user': response_dict,
                'message': 'User permissions updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating user permissions", error=str(e), user_id=user_id)
            return {'error': 'Failed to update user permissions', 'status': 'error'}, 500
    
    @users_ns.doc('get_user_permissions')
    def get(self, user_id):
        """Get user permissions"""
        try:
            db = get_db()
            collection = db.users
            
            # Find user
            query = {'user_id': user_id}
            if ObjectId.is_valid(user_id):
                query = {'$or': [{'user_id': user_id}, {'_id': ObjectId(user_id)}]}
            
            user_doc = collection.find_one(query)
            if not user_doc:
                return {'error': 'User not found', 'status': 'error'}, 404
            
            user = User().from_dict(user_doc)
            
            return {
                'user_id': user.user_id,
                'username': user.username,
                'role': user.role,
                'permissions': user.permissions,
                'message': 'User permissions retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching user permissions", error=str(e), user_id=user_id)
            return {'error': 'Failed to fetch user permissions', 'status': 'error'}, 500 
"""
Supplier routes
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
import structlog

from backend.models.supplier_model import Supplier
from backend.services.db_service import get_db

logger = structlog.get_logger()

suppliers_ns = Namespace('suppliers', description='Supplier management endpoints')

# API Models for documentation
supplier_model = suppliers_ns.model('Supplier', {
    'supplier_id': fields.String(description='Supplier ID'),
    'name': fields.String(required=True, description='Supplier name'),
    'company_name': fields.String(description='Company name'),
    'contact_email': fields.String(required=True, description='Contact email'),
    'contact_phone': fields.String(description='Contact phone'),
    'contact_person': fields.String(description='Contact person'),
    'address': fields.Raw(description='Address object'),
    'website': fields.String(description='Website URL'),
    'payment_terms': fields.String(description='Payment terms'),
    'lead_time_days': fields.Integer(description='Lead time in days'),
    'minimum_order_value': fields.Float(description='Minimum order value'),
    'rating': fields.Float(description='Supplier rating'),
    'status': fields.String(description='Supplier status'),
    'categories': fields.List(fields.String, description='Product categories')
})

@suppliers_ns.route('/')
class SupplierList(Resource):
    """Supplier list endpoint"""
    
    @suppliers_ns.doc('list_suppliers')
    def get(self):
        """Get all suppliers with optional filtering"""
        try:
            db = get_db()
            collection = db.suppliers
            
            # Get query parameters
            status = request.args.get('status', 'active')
            category = request.args.get('category')
            min_rating = request.args.get('min_rating', type=float)
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Build filter
            filter_query = {}
            if status:
                filter_query['status'] = status
            if category:
                filter_query['categories'] = {'$in': [category]}
            if min_rating:
                filter_query['rating'] = {'$gte': min_rating}
            
            # Execute query with pagination
            skip = (page - 1) * per_page
            cursor = collection.find(filter_query).skip(skip).limit(per_page)
            suppliers = []
            
            for supplier_doc in cursor:
                supplier = Supplier().from_dict(supplier_doc)
                suppliers.append(supplier.to_dict())
            
            # Get total count
            total_count = collection.count_documents(filter_query)
            
            return {
                'suppliers': suppliers,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'message': f'Retrieved {len(suppliers)} suppliers',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching suppliers", error=str(e))
            return {'error': 'Failed to fetch suppliers', 'status': 'error'}, 500
    
    @suppliers_ns.doc('create_supplier')
    @suppliers_ns.expect(supplier_model)
    def post(self):
        """Create new supplier"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
                
            # Create supplier instance
            supplier = Supplier()
            supplier.from_dict(data)
            
            # Validate required fields
            if not supplier.validate():
                return {'error': 'Missing required fields', 'status': 'error'}, 400
            
            # Check if supplier name already exists
            db = get_db()
            collection = db.suppliers
            if collection.find_one({'name': supplier.name}):
                return {'error': 'Supplier name already exists', 'status': 'error'}, 409
            
            # Save to database
            supplier.before_save()
            supplier_dict = supplier.to_dict()
            result = collection.insert_one(supplier_dict)
            
            # Return created supplier
            created_supplier = collection.find_one({'_id': result.inserted_id})
            response_supplier = Supplier().from_dict(created_supplier)
            
            return {
                'supplier': response_supplier.to_dict(),
                'message': 'Supplier created successfully',
                'status': 'success'
            }, 201
            
        except Exception as e:
            logger.error("Error creating supplier", error=str(e))
            return {'error': 'Failed to create supplier', 'status': 'error'}, 500


@suppliers_ns.route('/<string:supplier_id>')
@suppliers_ns.param('supplier_id', 'Supplier identifier')
class SupplierDetail(Resource):
    """Single supplier operations"""
    
    @suppliers_ns.doc('get_supplier')
    def get(self, supplier_id):
        """Get supplier by ID"""
        try:
            db = get_db()
            collection = db.suppliers
            
            # Find by supplier_id or _id
            query = {'supplier_id': supplier_id}
            if ObjectId.is_valid(supplier_id):
                query = {'$or': [{'supplier_id': supplier_id}, {'_id': ObjectId(supplier_id)}]}
            
            supplier_doc = collection.find_one(query)
            if not supplier_doc:
                return {'error': 'Supplier not found', 'status': 'error'}, 404
            
            supplier = Supplier().from_dict(supplier_doc)
            return {
                'supplier': supplier.to_dict(),
                'message': 'Supplier retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching supplier", error=str(e), supplier_id=supplier_id)
            return {'error': 'Failed to fetch supplier', 'status': 'error'}, 500
    
    @suppliers_ns.doc('update_supplier')
    @suppliers_ns.expect(supplier_model)
    def put(self, supplier_id):
        """Update supplier"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.suppliers
            
            # Find existing supplier
            query = {'supplier_id': supplier_id}
            if ObjectId.is_valid(supplier_id):
                query = {'$or': [{'supplier_id': supplier_id}, {'_id': ObjectId(supplier_id)}]}
            
            existing_supplier = collection.find_one(query)
            if not existing_supplier:
                return {'error': 'Supplier not found', 'status': 'error'}, 404
            
            # Update supplier
            supplier = Supplier().from_dict(existing_supplier)
            
            # Update fields from request data
            for key, value in data.items():
                if hasattr(supplier, key) and key not in ['_id', 'created_at']:
                    setattr(supplier, key, value)
            
            # Validate and save
            if not supplier.validate():
                return {'error': 'Invalid supplier data', 'status': 'error'}, 400
            
            supplier.before_save()
            supplier_dict = supplier.to_dict()
            
            # Remove _id for update
            if '_id' in supplier_dict:
                del supplier_dict['_id']
            
            collection.update_one(query, {'$set': supplier_dict})
            
            # Return updated supplier
            updated_supplier = collection.find_one(query)
            response_supplier = Supplier().from_dict(updated_supplier)
            
            return {
                'supplier': response_supplier.to_dict(),
                'message': 'Supplier updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating supplier", error=str(e), supplier_id=supplier_id)
            return {'error': 'Failed to update supplier', 'status': 'error'}, 500
    
    @suppliers_ns.doc('delete_supplier')
    def delete(self, supplier_id):
        """Delete supplier"""
        try:
            db = get_db()
            collection = db.suppliers
            
            # Check if supplier has associated products
            products_collection = db.products
            if products_collection.find_one({'supplier_id': supplier_id}):
                return {'error': 'Cannot delete supplier with associated products', 'status': 'error'}, 409
            
            # Find by supplier_id or _id
            query = {'supplier_id': supplier_id}
            if ObjectId.is_valid(supplier_id):
                query = {'$or': [{'supplier_id': supplier_id}, {'_id': ObjectId(supplier_id)}]}
            
            result = collection.delete_one(query)
            if result.deleted_count == 0:
                return {'error': 'Supplier not found', 'status': 'error'}, 404
            
            return {
                'message': 'Supplier deleted successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error deleting supplier", error=str(e), supplier_id=supplier_id)
            return {'error': 'Failed to delete supplier', 'status': 'error'}, 500


@suppliers_ns.route('/<string:supplier_id>/products')
@suppliers_ns.param('supplier_id', 'Supplier identifier')
class SupplierProducts(Resource):
    """Supplier's products"""
    
    @suppliers_ns.doc('get_supplier_products')
    def get(self, supplier_id):
        """Get all products for a supplier"""
        try:
            db = get_db()
            products_collection = db.products
            
            # Find products for this supplier
            products_cursor = products_collection.find({'supplier_id': supplier_id})
            products = []
            
            for product_doc in products_cursor:
                from backend.models.product_model import Product
                product = Product().from_dict(product_doc)
                products.append(product.to_dict())
            
            return {
                'supplier_id': supplier_id,
                'products': products,
                'count': len(products),
                'message': f'Retrieved {len(products)} products for supplier',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching supplier products", error=str(e), supplier_id=supplier_id)
            return {'error': 'Failed to fetch supplier products', 'status': 'error'}, 500 
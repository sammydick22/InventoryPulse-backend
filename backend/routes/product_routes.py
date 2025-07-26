"""
Product routes
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
import structlog

from backend.models.product_model import Product
from backend.services.db_service import get_db
from backend.utils.errors import ValidationError, NotFoundError

logger = structlog.get_logger()

products_ns = Namespace('products', description='Product management endpoints')

# API Models for documentation
product_model = products_ns.model('Product', {
    'product_id': fields.String(description='Product ID'),
    'name': fields.String(required=True, description='Product name'),
    'category': fields.String(required=True, description='Product category'),
    'sku': fields.String(required=True, description='Stock keeping unit'),
    'supplier_id': fields.String(required=True, description='Supplier ID'),
    'current_stock': fields.Float(description='Current stock level'),
    'reorder_threshold': fields.Float(description='Reorder threshold'),
    'reorder_quantity': fields.Float(description='Reorder quantity'),
    'cost_price': fields.Float(description='Cost price'),
    'selling_price': fields.Float(description='Selling price'),
    'description': fields.String(description='Product description'),
    'status': fields.String(description='Product status')
})

@products_ns.route('/')
class ProductList(Resource):
    """Product list endpoint"""
    
    @products_ns.doc('list_products')
    def get(self):
        """Get all products with optional filtering"""
        try:
            db = get_db()
            collection = db.products
            
            # Get query parameters
            category = request.args.get('category')
            status = request.args.get('status', 'active')
            supplier_id = request.args.get('supplier_id')
            low_stock = request.args.get('low_stock', type=bool)
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Build filter
            filter_query = {}
            if category:
                filter_query['category'] = category
            if status:
                filter_query['status'] = status
            if supplier_id:
                filter_query['supplier_id'] = supplier_id
            if low_stock:
                filter_query['$expr'] = {'$lte': ['$current_stock', '$reorder_threshold']}
            
            # Execute query with pagination
            skip = (page - 1) * per_page
            cursor = collection.find(filter_query).skip(skip).limit(per_page)
            products = []
            
            for product_doc in cursor:
                product = Product().from_dict(product_doc)
                products.append(product.to_dict())
            
            # Get total count
            total_count = collection.count_documents(filter_query)
            
            return {
                'products': products,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'message': f'Retrieved {len(products)} products',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching products", error=str(e))
            return {'error': 'Failed to fetch products', 'status': 'error'}, 500
    
    @products_ns.doc('create_product')
    @products_ns.expect(product_model)
    def post(self):
        """Create new product"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
                
            # Create product instance
            product = Product()
            product.from_dict(data)
            
            # Validate required fields
            if not product.validate():
                return {'error': 'Missing required fields', 'status': 'error'}, 400
            
            # Check if SKU already exists
            db = get_db()
            collection = db.products
            if collection.find_one({'sku': product.sku}):
                return {'error': 'SKU already exists', 'status': 'error'}, 409
            
            # Save to database
            product.before_save()
            product_dict = product.to_dict()
            result = collection.insert_one(product_dict)
            
            # Return created product
            created_product = collection.find_one({'_id': result.inserted_id})
            response_product = Product().from_dict(created_product)
            
            return {
                'product': response_product.to_dict(),
                'message': 'Product created successfully',
                'status': 'success'
            }, 201
            
        except Exception as e:
            logger.error("Error creating product", error=str(e))
            return {'error': 'Failed to create product', 'status': 'error'}, 500


@products_ns.route('/<string:product_id>')
@products_ns.param('product_id', 'Product identifier')
class ProductDetail(Resource):
    """Single product operations"""
    
    @products_ns.doc('get_product')
    def get(self, product_id):
        """Get product by ID"""
        try:
            db = get_db()
            collection = db.products
            
            # Find by product_id or _id
            query = {'product_id': product_id}
            if ObjectId.is_valid(product_id):
                query = {'$or': [{'product_id': product_id}, {'_id': ObjectId(product_id)}]}
            
            product_doc = collection.find_one(query)
            if not product_doc:
                return {'error': 'Product not found', 'status': 'error'}, 404
            
            product = Product().from_dict(product_doc)
            return {
                'product': product.to_dict(),
                'message': 'Product retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching product", error=str(e), product_id=product_id)
            return {'error': 'Failed to fetch product', 'status': 'error'}, 500
    
    @products_ns.doc('update_product')
    @products_ns.expect(product_model)
    def put(self, product_id):
        """Update product"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.products
            
            # Find existing product
            query = {'product_id': product_id}
            if ObjectId.is_valid(product_id):
                query = {'$or': [{'product_id': product_id}, {'_id': ObjectId(product_id)}]}
            
            existing_product = collection.find_one(query)
            if not existing_product:
                return {'error': 'Product not found', 'status': 'error'}, 404
            
            # Update product
            product = Product().from_dict(existing_product)
            
            # Update fields from request data
            for key, value in data.items():
                if hasattr(product, key) and key not in ['_id', 'created_at']:
                    setattr(product, key, value)
            
            # Validate and save
            if not product.validate():
                return {'error': 'Invalid product data', 'status': 'error'}, 400
            
            product.before_save()
            product_dict = product.to_dict()
            
            # Remove _id for update
            if '_id' in product_dict:
                del product_dict['_id']
            
            collection.update_one(query, {'$set': product_dict})
            
            # Return updated product
            updated_product = collection.find_one(query)
            response_product = Product().from_dict(updated_product)
            
            return {
                'product': response_product.to_dict(),
                'message': 'Product updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating product", error=str(e), product_id=product_id)
            return {'error': 'Failed to update product', 'status': 'error'}, 500
    
    @products_ns.doc('delete_product')
    def delete(self, product_id):
        """Delete product"""
        try:
            db = get_db()
            collection = db.products
            
            # Find by product_id or _id
            query = {'product_id': product_id}
            if ObjectId.is_valid(product_id):
                query = {'$or': [{'product_id': product_id}, {'_id': ObjectId(product_id)}]}
            
            result = collection.delete_one(query)
            if result.deleted_count == 0:
                return {'error': 'Product not found', 'status': 'error'}, 404
            
            return {
                'message': 'Product deleted successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error deleting product", error=str(e), product_id=product_id)
            return {'error': 'Failed to delete product', 'status': 'error'}, 500


@products_ns.route('/low-stock')
class LowStockProducts(Resource):
    """Products with low stock levels"""
    
    @products_ns.doc('low_stock_products')
    def get(self):
        """Get products with stock below reorder threshold"""
        try:
            db = get_db()
            collection = db.products
            
            # Find products where current_stock <= reorder_threshold
            pipeline = [
                {'$match': {'$expr': {'$lte': ['$current_stock', '$reorder_threshold']}}},
                {'$sort': {'current_stock': 1}}
            ]
            
            cursor = collection.aggregate(pipeline)
            products = []
            
            for product_doc in cursor:
                product = Product().from_dict(product_doc)
                products.append(product.to_dict())
            
            return {
                'products': products,
                'count': len(products),
                'message': f'Found {len(products)} products with low stock',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching low stock products", error=str(e))
            return {'error': 'Failed to fetch low stock products', 'status': 'error'}, 500 
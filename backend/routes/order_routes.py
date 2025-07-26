"""
Order routes for purchase order management
"""
from flask import request
from flask_restx import Namespace, Resource, fields
from bson import ObjectId
from datetime import datetime
import structlog

from backend.models.order_model import Order
from backend.services.db_service import get_db

logger = structlog.get_logger()

orders_ns = Namespace('orders', description='Purchase order management endpoints')

# API Models for documentation
order_item_model = orders_ns.model('OrderItem', {
    'product_id': fields.String(required=True, description='Product ID'),
    'product_name': fields.String(description='Product name'),
    'quantity': fields.Float(required=True, description='Quantity ordered'),
    'unit_price': fields.Float(required=True, description='Unit price'),
    'total_price': fields.Float(description='Total price for this item')
})

order_model = orders_ns.model('Order', {
    'order_id': fields.String(description='Order ID'),
    'supplier_id': fields.String(required=True, description='Supplier ID'),
    'status': fields.String(description='Order status'),
    'items': fields.List(fields.Nested(order_item_model), required=True, description='Order items'),
    'total_amount': fields.Float(description='Total order amount'),
    'currency': fields.String(description='Currency'),
    'expected_delivery_date': fields.String(description='Expected delivery date'),
    'shipping_address': fields.Raw(description='Shipping address'),
    'payment_method': fields.String(description='Payment method'),
    'notes': fields.String(description='Order notes'),
    'discount_percentage': fields.Float(description='Discount percentage'),
    'tax_amount': fields.Float(description='Tax amount'),
    'shipping_cost': fields.Float(description='Shipping cost')
})

@orders_ns.route('/')
class OrderList(Resource):
    """Order list endpoint"""
    
    @orders_ns.doc('list_orders')
    def get(self):
        """Get all orders with optional filtering"""
        try:
            db = get_db()
            collection = db.purchase_orders
            
            # Get query parameters
            status = request.args.get('status')
            supplier_id = request.args.get('supplier_id')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Build filter
            filter_query = {}
            if status:
                filter_query['status'] = status
            if supplier_id:
                filter_query['supplier_id'] = supplier_id
            
            # Date range filter
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter['$gte'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if end_date:
                    date_filter['$lte'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filter_query['order_date'] = date_filter
            
            # Execute query with pagination
            skip = (page - 1) * per_page
            cursor = collection.find(filter_query).sort('order_date', -1).skip(skip).limit(per_page)
            orders = []
            
            for order_doc in cursor:
                order = Order().from_dict(order_doc)
                orders.append(order.to_dict())
            
            # Get total count
            total_count = collection.count_documents(filter_query)
            
            return {
                'orders': orders,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'message': f'Retrieved {len(orders)} orders',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching orders", error=str(e))
            return {'error': 'Failed to fetch orders', 'status': 'error'}, 500
    
    @orders_ns.doc('create_order')
    @orders_ns.expect(order_model)
    def post(self):
        """Create new purchase order"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
                
            # Create order instance
            order = Order()
            order.from_dict(data)
            
            # Validate required fields
            if not order.validate():
                return {'error': 'Missing required fields', 'status': 'error'}, 400
            
            # Verify supplier exists
            db = get_db()
            suppliers_collection = db.suppliers
            if not suppliers_collection.find_one({'supplier_id': order.supplier_id}):
                return {'error': 'Supplier not found', 'status': 'error'}, 404
            
            # Verify products exist and update stock
            products_collection = db.products
            for item in order.items:
                product = products_collection.find_one({'product_id': item['product_id']})
                if not product:
                    return {'error': f'Product {item["product_id"]} not found', 'status': 'error'}, 404
                
                # Set product name if not provided
                if not item.get('product_name'):
                    item['product_name'] = product.get('name', 'Unknown Product')
            
            # Save to database
            order.before_save()
            orders_collection = db.purchase_orders
            order_dict = order.to_dict()
            result = orders_collection.insert_one(order_dict)
            
            # Return created order
            created_order = orders_collection.find_one({'_id': result.inserted_id})
            response_order = Order().from_dict(created_order)
            
            return {
                'order': response_order.to_dict(),
                'message': 'Order created successfully',
                'status': 'success'
            }, 201
            
        except Exception as e:
            logger.error("Error creating order", error=str(e))
            return {'error': 'Failed to create order', 'status': 'error'}, 500


@orders_ns.route('/<string:order_id>')
@orders_ns.param('order_id', 'Order identifier')
class OrderDetail(Resource):
    """Single order operations"""
    
    @orders_ns.doc('get_order')
    def get(self, order_id):
        """Get order by ID"""
        try:
            db = get_db()
            collection = db.purchase_orders
            
            # Find by order_id or _id
            query = {'order_id': order_id}
            if ObjectId.is_valid(order_id):
                query = {'$or': [{'order_id': order_id}, {'_id': ObjectId(order_id)}]}
            
            order_doc = collection.find_one(query)
            if not order_doc:
                return {'error': 'Order not found', 'status': 'error'}, 404
            
            order = Order().from_dict(order_doc)
            return {
                'order': order.to_dict(),
                'message': 'Order retrieved successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching order", error=str(e), order_id=order_id)
            return {'error': 'Failed to fetch order', 'status': 'error'}, 500
    
    @orders_ns.doc('update_order')
    @orders_ns.expect(order_model)
    def put(self, order_id):
        """Update order"""
        try:
            data = request.get_json()
            if not data:
                return {'error': 'No data provided', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.purchase_orders
            
            # Find existing order
            query = {'order_id': order_id}
            if ObjectId.is_valid(order_id):
                query = {'$or': [{'order_id': order_id}, {'_id': ObjectId(order_id)}]}
            
            existing_order = collection.find_one(query)
            if not existing_order:
                return {'error': 'Order not found', 'status': 'error'}, 404
            
            # Check if order can be updated (not if it's delivered or cancelled)
            current_status = existing_order.get('status', '')
            if current_status in ['delivered', 'cancelled']:
                return {'error': f'Cannot update {current_status} order', 'status': 'error'}, 409
            
            # Update order
            order = Order().from_dict(existing_order)
            
            # Update fields from request data
            for key, value in data.items():
                if hasattr(order, key) and key not in ['_id', 'created_at', 'order_id']:
                    setattr(order, key, value)
            
            # Validate and save
            if not order.validate():
                return {'error': 'Invalid order data', 'status': 'error'}, 400
            
            order.before_save()
            order_dict = order.to_dict()
            
            # Remove _id for update
            if '_id' in order_dict:
                del order_dict['_id']
            
            collection.update_one(query, {'$set': order_dict})
            
            # Return updated order
            updated_order = collection.find_one(query)
            response_order = Order().from_dict(updated_order)
            
            return {
                'order': response_order.to_dict(),
                'message': 'Order updated successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating order", error=str(e), order_id=order_id)
            return {'error': 'Failed to update order', 'status': 'error'}, 500
    
    @orders_ns.doc('delete_order')
    def delete(self, order_id):
        """Cancel/Delete order"""
        try:
            db = get_db()
            collection = db.purchase_orders
            
            # Find existing order
            query = {'order_id': order_id}
            if ObjectId.is_valid(order_id):
                query = {'$or': [{'order_id': order_id}, {'_id': ObjectId(order_id)}]}
            
            existing_order = collection.find_one(query)
            if not existing_order:
                return {'error': 'Order not found', 'status': 'error'}, 404
            
            # Check if order can be cancelled
            current_status = existing_order.get('status', '')
            if current_status in ['delivered', 'shipped']:
                return {'error': f'Cannot cancel {current_status} order', 'status': 'error'}, 409
            
            # Update status to cancelled instead of deleting
            collection.update_one(query, {'$set': {
                'status': 'cancelled',
                'updated_at': datetime.utcnow().isoformat()
            }})
            
            return {
                'message': 'Order cancelled successfully',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error cancelling order", error=str(e), order_id=order_id)
            return {'error': 'Failed to cancel order', 'status': 'error'}, 500


@orders_ns.route('/status/<string:status>')
@orders_ns.param('status', 'Order status (pending, confirmed, shipped, delivered, cancelled)')
class OrdersByStatus(Resource):
    """Orders filtered by status"""
    
    @orders_ns.doc('get_orders_by_status')
    def get(self, status):
        """Get orders by status"""
        try:
            db = get_db()
            collection = db.purchase_orders
            
            # Validate status
            valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
            if status not in valid_statuses:
                return {'error': f'Invalid status. Must be one of: {valid_statuses}', 'status': 'error'}, 400
            
            # Find orders with specified status
            cursor = collection.find({'status': status}).sort('order_date', -1)
            orders = []
            
            for order_doc in cursor:
                order = Order().from_dict(order_doc)
                orders.append(order.to_dict())
            
            return {
                'orders': orders,
                'status_filter': status,
                'count': len(orders),
                'message': f'Retrieved {len(orders)} orders with status: {status}',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching orders by status", error=str(e), status=status)
            return {'error': 'Failed to fetch orders by status', 'status': 'error'}, 500


@orders_ns.route('/<string:order_id>/status')
@orders_ns.param('order_id', 'Order identifier')
class OrderStatus(Resource):
    """Update order status"""
    
    @orders_ns.doc('update_order_status')
    def put(self, order_id):
        """Update order status"""
        try:
            data = request.get_json()
            if not data or 'status' not in data:
                return {'error': 'Status is required', 'status': 'error'}, 400
            
            new_status = data['status']
            valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
            if new_status not in valid_statuses:
                return {'error': f'Invalid status. Must be one of: {valid_statuses}', 'status': 'error'}, 400
            
            db = get_db()
            collection = db.purchase_orders
            
            # Find order
            query = {'order_id': order_id}
            if ObjectId.is_valid(order_id):
                query = {'$or': [{'order_id': order_id}, {'_id': ObjectId(order_id)}]}
            
            existing_order = collection.find_one(query)
            if not existing_order:
                return {'error': 'Order not found', 'status': 'error'}, 404
            
            # Update status and related fields
            update_data = {
                'status': new_status,
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Set delivery date if status is delivered
            if new_status == 'delivered':
                update_data['actual_delivery_date'] = datetime.utcnow().isoformat()
            
            collection.update_one(query, {'$set': update_data})
            
            # Return updated order
            updated_order = collection.find_one(query)
            response_order = Order().from_dict(updated_order)
            
            return {
                'order': response_order.to_dict(),
                'message': f'Order status updated to {new_status}',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error updating order status", error=str(e), order_id=order_id)
            return {'error': 'Failed to update order status', 'status': 'error'}, 500 

@orders_ns.route('/purchase')
class PurchaseOrderList(Resource):
    """Backward compatibility endpoint for purchase orders"""
    
    @orders_ns.doc('list_purchase_orders_legacy')
    def get(self):
        """Get all purchase orders (legacy endpoint)"""
        # Redirect to the main orders endpoint with the same logic
        try:
            db = get_db()
            collection = db.purchase_orders
            
            # Get query parameters
            status = request.args.get('status')
            supplier_id = request.args.get('supplier_id')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            
            # Build filter
            filter_query = {}
            if status:
                filter_query['status'] = status
            if supplier_id:
                filter_query['supplier_id'] = supplier_id
            
            # Date range filter
            if start_date or end_date:
                date_filter = {}
                if start_date:
                    date_filter['$gte'] = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                if end_date:
                    date_filter['$lte'] = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                filter_query['order_date'] = date_filter
            
            # Execute query with pagination
            skip = (page - 1) * per_page
            cursor = collection.find(filter_query).sort('order_date', -1).skip(skip).limit(per_page)
            orders = []
            
            for order_doc in cursor:
                order = Order().from_dict(order_doc)
                orders.append(order.to_dict())
            
            # Get total count
            total_count = collection.count_documents(filter_query)
            
            return {
                'purchase_orders': orders,  # Use legacy key name
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': total_count,
                    'pages': (total_count + per_page - 1) // per_page
                },
                'message': f'Retrieved {len(orders)} purchase orders',
                'status': 'success'
            }
            
        except Exception as e:
            logger.error("Error fetching purchase orders", error=str(e))
            return {'error': 'Failed to fetch purchase orders', 'status': 'error'}, 500 
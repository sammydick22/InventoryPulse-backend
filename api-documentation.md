# InventoryPulse API Documentation

## Overview

This document provides complete API documentation for the InventoryPulse backend services. The API follows RESTful conventions and returns JSON responses.

**Base URL**: `https://your-domain.com/api`  
**Authentication**: Bearer Token (JWT)  
**Content-Type**: `application/json`

## Authentication

### Login
```http
POST /api/auth/login
```

**Request Body**:
```json
{
  "email": "user@company.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "USR123456",
    "email": "user@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "role": "manager"
  },
  "expires_in": 3600
}
```

### Check Authentication Status
```http
GET /api/auth/status
```

**Headers**: `Authorization: Bearer {token}`

**Response**:
```json
{
  "valid": true,
  "user": {
    "user_id": "USR123456",
    "email": "user@company.com",
    "role": "manager"
  },
  "expires_at": "2025-01-26T10:30:00Z"
}
```

## Inventory Management

### Get All Products
```http
GET /api/inventory
```

**Query Parameters**:
- `category` (optional): Filter by product category
- `low_stock` (optional): "true" to show only low stock items
- `status` (optional): Filter by product status (active, discontinued, etc.)
- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Items per page (default: 50, max: 200)

**Response**:
```json
{
  "products": [
    {
      "product_id": "WIDGET001",
      "name": "Industrial Widget Type A",
      "category": "components",
      "current_quantity": 42,
      "available_quantity": 40,
      "reserved_quantity": 2,
      "reorder_threshold": 10,
      "max_stock_level": 500,
      "unit_cost": 12.99,
      "unit_price": 19.99,
      "unit_of_measure": "each",
      "location": {
        "warehouse": "MAIN",
        "zone": "A",
        "aisle": "A1",
        "shelf": "3"
      },
      "suppliers": [
        {
          "supplier_id": "SUPACME001",
          "supplier_name": "ACME Industrial",
          "is_primary": true,
          "lead_time_days": 7,
          "last_price": 11.50,
          "last_checked": "2025-01-25T10:00:00Z"
        }
      ],
      "status": "active",
      "last_sale_date": "2025-01-24T15:30:00Z",
      "last_restock_date": "2025-01-20T09:00:00Z",
      "created_at": "2025-01-01T00:00:00Z",
      "updated_at": "2025-01-25T10:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 150,
    "pages": 3
  }
}
```

### Get Single Product
```http
GET /api/inventory/{product_id}
```

**Path Parameters**:
- `product_id`: Product identifier (e.g., "WIDGET001")

**Response**:
```json
{
  "product_id": "WIDGET001",
  "name": "Industrial Widget Type A",
  "description": "High-quality industrial widget for manufacturing applications",
  "category": "components",
  "subcategory": "mechanical",
  "current_quantity": 42,
  "available_quantity": 40,
  "reserved_quantity": 2,
  "reorder_threshold": 10,
  "max_stock_level": 500,
  "unit_cost": 12.99,
  "unit_price": 19.99,
  "unit_of_measure": "each",
  "location": {
    "warehouse": "MAIN",
    "zone": "A",
    "aisle": "A1",
    "shelf": "3"
  },
  "suppliers": [
    {
      "supplier_id": "SUPACME001",
      "supplier_name": "ACME Industrial",
      "supplier_product_code": "ACME-WGT-001",
      "is_primary": true,
      "lead_time_days": 7,
      "min_order_quantity": 50,
      "last_price": 11.50,
      "last_checked": "2025-01-25T10:00:00Z"
    }
  ],
  "attributes": {
    "color": "silver",
    "material": "aluminum",
    "weight_kg": 0.5
  },
  "status": "active",
  "last_sale_date": "2025-01-24T15:30:00Z",
  "last_restock_date": "2025-01-20T09:00:00Z",
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-25T10:30:00Z",
  "tags": ["industrial", "mechanical", "aluminum"]
}
```

### Get Low Stock Items
```http
GET /api/inventory/low-stock
```

**Query Parameters**:
- `threshold_override` (optional): Override default threshold

**Response**:
```json
{
  "low_stock_items": [
    {
      "product_id": "WIDGET002",
      "name": "Widget Type B",
      "current_quantity": 5,
      "reorder_threshold": 10,
      "recommended_reorder_qty": 100,
      "urgency": "high",
      "days_until_stockout": 3,
      "suppliers": [
        {
          "supplier_id": "SUPACME001",
          "supplier_name": "ACME Industrial",
          "lead_time_days": 7,
          "available_qty": 500
        }
      ]
    }
  ],
  "total_items": 5,
  "critical_count": 2,
  "high_priority_count": 3
}
```

### Update Product Stock
```http
PUT /api/inventory/{product_id}
```

**Request Body**:
```json
{
  "current_quantity": 75,
  "reason": "Manual stock adjustment after inventory count",
  "performed_by": "USR123456"
}
```

**Response**:
```json
{
  "product_id": "WIDGET001",
  "previous_quantity": 42,
  "updated_quantity": 75,
  "difference": 33,
  "status": "updated successfully",
  "transaction_id": "TXN789012",
  "updated_at": "2025-01-25T11:00:00Z"
}
```

### Create New Product
```http
POST /api/inventory
```

**Request Body**:
```json
{
  "product_id": "NEWPART001",
  "name": "New Component Part",
  "description": "Description of the new part",
  "category": "components",
  "subcategory": "electronic",
  "current_quantity": 100,
  "reorder_threshold": 20,
  "max_stock_level": 1000,
  "unit_cost": 5.99,
  "unit_price": 9.99,
  "unit_of_measure": "each",
  "location": {
    "warehouse": "MAIN",
    "zone": "B",
    "aisle": "B2",
    "shelf": "1"
  },
  "suppliers": [
    {
      "supplier_id": "SUPACME001",
      "is_primary": true,
      "lead_time_days": 5,
      "min_order_quantity": 25
    }
  ],
  "attributes": {
    "voltage": "12V",
    "current": "2A"
  },
  "tags": ["electronic", "new"]
}
```

**Response**:
```json
{
  "product_id": "NEWPART001",
  "status": "created successfully",
  "created_at": "2025-01-25T11:15:00Z"
}
```

## Supplier Management

### Get Supplier Information for Product
```http
GET /api/suppliers/{product_id}
```

**Response**:
```json
{
  "product_id": "WIDGET001",
  "suppliers": [
    {
      "supplier_id": "SUPACME001",
      "supplier_name": "ACME Industrial",
      "contact_info": {
        "email": "orders@acme-industrial.com",
        "phone": "+1-555-0123"
      },
      "current_availability": {
        "on_hand": 1500,
        "price": 11.50,
        "lead_time_days": 7,
        "last_checked": "2025-01-25T10:00:00Z"
      },
      "performance_metrics": {
        "avg_lead_time_days": 6,
        "on_time_delivery_rate": 0.95,
        "quality_score": 4.2,
        "price_competitiveness": 4.0
      },
      "status": "active"
    }
  ]
}
```

### Get All Suppliers
```http
GET /api/suppliers
```

**Response**:
```json
{
  "suppliers": [
    {
      "supplier_id": "SUPACME001",
      "name": "ACME Industrial",
      "contact_info": {
        "email": "orders@acme-industrial.com",
        "phone": "+1-555-0123",
        "website": "https://acme-industrial.com"
      },
      "api_config": {
        "has_api": true,
        "last_sync_at": "2025-01-25T10:00:00Z",
        "sync_frequency_hours": 6
      },
      "performance_metrics": {
        "avg_lead_time_days": 6,
        "on_time_delivery_rate": 0.95,
        "quality_score": 4.2
      },
      "status": "active",
      "product_count": 45
    }
  ]
}
```

## Orders Management

### Get All Orders
```http
GET /api/orders
```

**Query Parameters**:
- `status` (optional): Filter by order status
- `supplier_id` (optional): Filter by supplier
- `start_date` (optional): Filter by order date range
- `end_date` (optional): Filter by order date range

**Response**:
```json
{
  "orders": [
    {
      "order_id": "PO20250001",
      "supplier_id": "SUPACME001",
      "supplier_name": "ACME Industrial",
      "items": [
        {
          "product_id": "WIDGET001",
          "product_name": "Industrial Widget Type A",
          "quantity": 100,
          "unit_price": 11.50,
          "total_price": 1150.00
        }
      ],
      "total_amount": 1150.00,
      "currency": "USD",
      "status": "confirmed",
      "priority": "normal",
      "order_date": "2025-01-25T00:00:00Z",
      "expected_delivery_date": "2025-02-01T00:00:00Z",
      "created_by": "USR123456",
      "created_at": "2025-01-25T09:00:00Z"
    }
  ]
}
```

### Create New Order
```http
POST /api/orders
```

**Request Body**:
```json
{
  "supplier_id": "SUPACME001",
  "items": [
    {
      "product_id": "WIDGET001",
      "quantity": 100,
      "unit_price": 11.50
    },
    {
      "product_id": "WIDGET002",
      "quantity": 50,
      "unit_price": 8.75
    }
  ],
  "priority": "normal",
  "expected_delivery_date": "2025-02-01T00:00:00Z",
  "notes": "Rush order for production line"
}
```

**Response**:
```json
{
  "order_id": "PO20250002",
  "status": "created",
  "total_amount": 1587.50,
  "currency": "USD",
  "estimated_delivery": "2025-02-01T00:00:00Z",
  "created_at": "2025-01-25T11:30:00Z"
}
```

### Update Order Status
```http
PUT /api/orders/{order_id}
```

**Request Body**:
```json
{
  "status": "shipped",
  "actual_delivery_date": "2025-01-30T14:00:00Z",
  "notes": "Tracking number: ABC123456"
}
```

**Response**:
```json
{
  "order_id": "PO20250001",
  "previous_status": "confirmed",
  "updated_status": "shipped",
  "updated_at": "2025-01-25T11:45:00Z"
}
```

## Insights and Recommendations

### Get Current Recommendations
```http
GET /api/insights/recommendation
```

**Query Parameters**:
- `product_id` (optional): Get recommendations for specific product
- `type` (optional): Filter by insight type
- `priority` (optional): Filter by priority level

**Response**:
```json
{
  "recommendations": [
    {
      "insight_id": "INS789012",
      "type": "reorder",
      "priority": "high",
      "product_id": "WIDGET001",
      "message": "Widget Type A stock is below threshold. Only 5 units left, supplier has 1500 available. Recommended to order 100 units by Feb 1st to avoid stockout.",
      "data": {
        "current_stock": 5,
        "threshold": 10,
        "recommended_order": 100,
        "supplier_availability": 1500,
        "predicted_stockout_date": "2025-02-03"
      },
      "action_taken": false,
      "expires_at": "2025-02-01T00:00:00Z",
      "created_by": "ai_agent",
      "created_at": "2025-01-25T08:00:00Z"
    }
  ],
  "summary": {
    "total_insights": 8,
    "critical": 1,
    "high": 3,
    "medium": 4,
    "unacknowledged": 6
  }
}
```

### Get Demand Forecast
```http
GET /api/insights/forecast/{product_id}
```

**Query Parameters**:
- `period` (optional): Forecast period (30, 60, 90 days)
- `granularity` (optional): daily, weekly, monthly

**Response**:
```json
{
  "product_id": "WIDGET001",
  "forecast_period": "next_30_days",
  "predicted_demand": 120,
  "confidence_interval": {
    "lower": 100,
    "upper": 140
  },
  "trend": "increasing",
  "seasonality_factor": 1.15,
  "breakdown": [
    {
      "period": "week_1",
      "predicted_demand": 25,
      "confidence": 0.85
    },
    {
      "period": "week_2",
      "predicted_demand": 28,
      "confidence": 0.82
    }
  ],
  "model_info": {
    "model_type": "ARIMA",
    "model_version": "v2.1",
    "accuracy_score": 0.87,
    "last_trained": "2025-01-24T02:00:00Z"
  },
  "generated_at": "2025-01-25T06:00:00Z"
}
```

### Acknowledge Insight
```http
POST /api/insights/{insight_id}/acknowledge
```

**Request Body**:
```json
{
  "action_taken": true,
  "action_details": "Created purchase order PO20250002 for 100 units"
}
```

**Response**:
```json
{
  "insight_id": "INS789012",
  "acknowledged_at": "2025-01-25T12:00:00Z",
  "acknowledged_by": "USR123456",
  "status": "acknowledged"
}
```

## Advanced Features

### AI Agent Query (Natural Language)
```http
POST /api/agent/query
```

**Request Body**:
```json
{
  "query": "What products are likely to stock out in the next two weeks?",
  "context": {
    "user_id": "USR123456",
    "session_id": "sess_789"
  }
}
```

**Response**:
```json
{
  "answer": "Based on current inventory levels and demand forecasts, 3 products are likely to stock out in the next two weeks: Widget Type B (5 days), Electronic Component C (8 days), and Industrial Part D (12 days). I recommend prioritizing orders for these items.",
  "structured_data": {
    "at_risk_products": [
      {
        "product_id": "WIDGET002",
        "current_stock": 5,
        "predicted_stockout_days": 5,
        "recommended_action": "urgent_reorder"
      }
    ]
  },
  "confidence": 0.89,
  "sources": ["inventory_data", "demand_forecast", "supplier_availability"],
  "processing_time_ms": 1250
}
```

### Transaction History
```http
GET /api/inventory/{product_id}/transactions
```

**Query Parameters**:
- `start_date` (optional): Filter by date range
- `end_date` (optional): Filter by date range
- `type` (optional): Filter by transaction type
- `limit` (optional): Number of records to return

**Response**:
```json
{
  "product_id": "WIDGET001",
  "transactions": [
    {
      "transaction_id": "TXN789012",
      "type": "purchase",
      "quantity": 100,
      "unit_cost": 11.50,
      "total_value": 1150.00,
      "reference_id": "PO20250001",
      "reason": "Restock from supplier",
      "performed_by": "system",
      "timestamp": "2025-01-25T09:00:00Z"
    },
    {
      "transaction_id": "TXN789011",
      "type": "sale",
      "quantity": -25,
      "unit_cost": 12.99,
      "total_value": -324.75,
      "reference_id": "SO20250045",
      "reason": "Customer order fulfillment",
      "performed_by": "USR123456",
      "timestamp": "2025-01-24T15:30:00Z"
    }
  ],
  "summary": {
    "total_transactions": 15,
    "net_quantity_change": 75,
    "total_value_change": 825.25
  }
}
```

## System Endpoints

### Health Check
```http
GET /api/health
```

**Response**:
```json
{
  "status": "ok",
  "timestamp": "2025-01-25T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "cache": "healthy",
    "external_apis": "healthy"
  },
  "uptime_seconds": 86400
}
```

### System Statistics
```http
GET /api/stats
```

**Response**:
```json
{
  "inventory": {
    "total_products": 1250,
    "active_products": 1180,
    "low_stock_items": 23,
    "out_of_stock_items": 5,
    "total_value": 1250000.50
  },
  "orders": {
    "pending_orders": 12,
    "this_month_orders": 45,
    "total_order_value_month": 125000.00
  },
  "insights": {
    "active_insights": 18,
    "critical_alerts": 3,
    "unacknowledged": 8
  },
  "last_updated": "2025-01-25T12:00:00Z"
}
```

## Error Handling

### Error Response Format
All API errors follow this format:

```json
{
  "error": {
    "code": "PRODUCT_NOT_FOUND",
    "message": "Product with ID 'INVALID001' was not found",
    "details": {
      "product_id": "INVALID001",
      "suggestion": "Check the product ID and try again"
    },
    "timestamp": "2025-01-25T12:00:00Z",
    "request_id": "req_789012"
  }
}
```

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **400 Bad Request**: Invalid request format or parameters
- **401 Unauthorized**: Authentication required or invalid token
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **409 Conflict**: Resource already exists or constraint violation
- **422 Unprocessable Entity**: Validation errors
- **429 Too Many Requests**: Rate limit exceeded
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

### Common Error Codes

- `INVALID_CREDENTIALS`: Login failed
- `TOKEN_EXPIRED`: JWT token has expired
- `PRODUCT_NOT_FOUND`: Product doesn't exist
- `SUPPLIER_NOT_FOUND`: Supplier doesn't exist
- `ORDER_NOT_FOUND`: Order doesn't exist
- `INSUFFICIENT_STOCK`: Not enough inventory for operation
- `VALIDATION_ERROR`: Request data validation failed
- `DUPLICATE_PRODUCT_ID`: Product ID already exists
- `INVALID_QUANTITY`: Quantity must be positive
- `SUPPLIER_UNAVAILABLE`: Supplier service is down

## Rate Limiting

API requests are rate limited to:
- **Authenticated users**: 1000 requests per hour
- **Unauthenticated requests**: 100 requests per hour
- **Bulk operations**: 50 requests per hour

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 750
X-RateLimit-Reset: 1642781400
```

## Pagination

Endpoints that return lists support pagination:

**Request Parameters**:
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50, max: 200)

**Response includes pagination info**:
```json
{
  "pagination": {
    "page": 1,
    "limit": 50,
    "total": 1250,
    "pages": 25,
    "has_next": true,
    "has_previous": false
  }
}
```

## WebSocket Events (Real-time Updates)

### Connection
```javascript
const ws = new WebSocket('wss://your-domain.com/ws');
ws.onopen = function() {
  // Send authentication
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your-jwt-token'
  }));
};
```

### Event Types

#### Stock Level Changes
```json
{
  "type": "stock_update",
  "data": {
    "product_id": "WIDGET001",
    "previous_quantity": 42,
    "new_quantity": 40,
    "change": -2,
    "reason": "sale",
    "timestamp": "2025-01-25T12:00:00Z"
  }
}
```

#### New Insights
```json
{
  "type": "new_insight",
  "data": {
    "insight_id": "INS789013",
    "type": "reorder",
    "priority": "high",
    "product_id": "WIDGET001",
    "message": "Stock level critically low",
    "created_at": "2025-01-25T12:00:00Z"
  }
}
```

#### Order Status Updates
```json
{
  "type": "order_update",
  "data": {
    "order_id": "PO20250001",
    "previous_status": "confirmed",
    "new_status": "shipped",
    "updated_at": "2025-01-25T12:00:00Z"
  }
}
```

## Environment Configuration

### Development
- Base URL: `http://localhost:5000/api`
- Rate Limits: Disabled
- Authentication: Optional for testing

### Staging
- Base URL: `https://staging-api.inventorypulse.com/api`
- Rate Limits: Enabled (reduced limits)
- Authentication: Required

### Production
- Base URL: `https://api.inventorypulse.com/api`
- Rate Limits: Full limits enforced
- Authentication: Required
- HTTPS Only: Yes

## SDK Examples

### JavaScript/TypeScript
```javascript
import InventoryPulseAPI from '@inventorypulse/api-client';

const api = new InventoryPulseAPI({
  baseURL: 'https://api.inventorypulse.com/api',
  token: 'your-jwt-token'
});

// Get all products
const products = await api.inventory.getAll();

// Get low stock items
const lowStock = await api.inventory.getLowStock();

// Create order
const order = await api.orders.create({
  supplier_id: 'SUPACME001',
  items: [{ product_id: 'WIDGET001', quantity: 100, unit_price: 11.50 }]
});
```

### Python
```python
from inventorypulse import InventoryPulseClient

client = InventoryPulseClient(
    base_url='https://api.inventorypulse.com/api',
    token='your-jwt-token'
)

# Get all products
products = client.inventory.get_all()

# Get low stock items
low_stock = client.inventory.get_low_stock()

# Create order
order = client.orders.create({
    'supplier_id': 'SUPACME001',
    'items': [{'product_id': 'WIDGET001', 'quantity': 100, 'unit_price': 11.50}]
})
```

This API documentation provides everything your frontend engineer needs to integrate with the InventoryPulse backend system. 
# InventoryPulse: Comprehensive Technical Specification

## Project Overview

**InventoryPulse** is an AI-powered inventory management system designed for small to medium-sized businesses. It provides intelligent demand forecasting, automated stock optimization, and real-time insights through conversational interfaces. The platform combines modern web technologies with artificial intelligence to help businesses maintain optimal inventory levels while minimizing costs.

**Core Value Proposition:** Transform reactive inventory management into proactive, AI-driven optimization that reduces stockouts by 60% and excess inventory by 40% while providing natural language interfaces for non-technical users.

**Technology stack and SaaS integrations:** InventoryPulse's backend is a microservice-oriented Flask application with MongoDB Atlas as its operational database for live inventory data. It integrates several SaaS platforms for extended capabilities: **Wiz** for continuous infrastructure security scanning, **Temporal** for orchestrating multi-step workflows across microservices/agents, **NLX** for a no-code conversational UI (supporting both chat and voice interactions), **MiniMax** for speech-to-text and text-to-speech services (ASR/TTS) and as the general LLM for AI-powered insights and recommendations, and **Snowflake** as a cloud data warehouse for historical data analytics and demand forecasting.

## **Database Schema Definitions**

### **MongoDB Atlas Collections**

#### **1. Products Collection (`products`)**
```javascript
{
  _id: ObjectId,                    // Primary key
  product_id: String,               // Unique business identifier (required, indexed)
  name: String,                     // Product name (required, max 200 chars)
  description: String,              // Product description (max 1000 chars)
  category: String,                 // Product category (required, indexed)
  subcategory: String,              // Product subcategory (optional)
  sku: String,                      // Stock Keeping Unit (required, unique, indexed)
  barcode: String,                  // Product barcode (optional, indexed if present)
  
  // Supplier Information
  supplier_id: ObjectId,            // Reference to suppliers collection (required, indexed)
  supplier_product_code: String,    // Supplier's internal product code (optional)
  
  // Inventory Tracking
  current_stock: Number,            // Current quantity in stock (required, >= 0)
  reserved_stock: Number,           // Stock reserved for pending orders (default: 0)
  available_stock: Number,          // Calculated: current_stock - reserved_stock
  reorder_threshold: Number,        // Low stock alert threshold (required, > 0)
  reorder_quantity: Number,         // Default quantity to reorder (required, > 0)
  max_stock_level: Number,          // Maximum stock capacity (optional)
  
  // Pricing
  cost_price: Number,               // Cost from supplier (required, >= 0, 2 decimal places)
  selling_price: Number,            // Retail price (required, >= cost_price, 2 decimal places)
  currency: String,                 // Currency code (default: "USD", 3 chars)
  
  // Physical Properties
  weight: Number,                   // Weight in grams (optional, >= 0)
  dimensions: {                     // Product dimensions (optional)
    length: Number,                 // Length in cm
    width: Number,                  // Width in cm
    height: Number                  // Height in cm
  },
  
  // Location & Organization
  warehouse_location: String,       // Physical location in warehouse (optional)
  storage_requirements: [String],   // e.g., ["temperature_controlled", "fragile"]
  
  // Metadata
  status: String,                   // "active", "discontinued", "pending" (default: "active")
  created_at: Date,                 // Document creation timestamp (auto-generated)
  updated_at: Date,                 // Last modification timestamp (auto-updated)
  created_by: ObjectId,             // User who created the record
  last_modified_by: ObjectId,       // User who last modified the record
  
  // Validation Rules
  tags: [String],                   // Search tags (max 20 tags, each max 50 chars)
  seasonal: Boolean,                // Whether product is seasonal (default: false)
  expiration_tracking: Boolean,     // Whether to track expiration dates (default: false)
  lot_tracking: Boolean             // Whether to track lot numbers (default: false)
}

// Indexes
db.products.createIndex({ "product_id": 1 }, { unique: true })
db.products.createIndex({ "sku": 1 }, { unique: true })
db.products.createIndex({ "supplier_id": 1 })
db.products.createIndex({ "category": 1, "subcategory": 1 })
db.products.createIndex({ "current_stock": 1 })
db.products.createIndex({ "barcode": 1 }, { sparse: true })
db.products.createIndex({ "name": "text", "description": "text" })
```

#### **2. Suppliers Collection (`suppliers`)**
```javascript
{
  _id: ObjectId,                    // Primary key
  supplier_id: String,              // Unique business identifier (required, indexed)
  company_name: String,             // Legal company name (required, max 200 chars)
  display_name: String,             // Short display name (optional, max 100 chars)
  
  // Contact Information
  contact: {
    primary_contact: String,        // Main contact person (required)
    email: String,                  // Primary email (required, validated email format)
    phone: String,                  // Primary phone (required, E.164 format)
    alternative_phone: String,      // Backup phone (optional)
    website: String                 // Company website (optional, URL format)
  },
  
  // Address Information
  address: {
    street: String,                 // Street address (required)
    city: String,                   // City (required)
    state: String,                  // State/Province (required)
    postal_code: String,            // ZIP/Postal code (required)
    country: String                 // Country code (required, ISO 3166-1 alpha-2)
  },
  
  // Business Details
  tax_id: String,                   // Tax identification number (optional)
  payment_terms: Number,            // Payment terms in days (default: 30)
  currency: String,                 // Preferred currency (default: "USD")
  lead_time_days: Number,           // Standard delivery lead time (required, >= 1)
  minimum_order_value: Number,      // Minimum order amount (default: 0)
  
  // Performance Metrics
  rating: Number,                   // Supplier rating 1-5 (default: 3, validated range)
  on_time_delivery_rate: Number,    // Percentage (0-100, default: null)
  quality_score: Number,            // Quality rating 1-5 (default: null)
  
  // Status & Metadata
  status: String,                   // "active", "inactive", "pending" (default: "active")
  preferred: Boolean,               // Preferred supplier flag (default: false)
  created_at: Date,                 // Auto-generated
  updated_at: Date,                 // Auto-updated
  created_by: ObjectId,             // User reference
  notes: String                     // Additional notes (max 1000 chars)
}

// Indexes
db.suppliers.createIndex({ "supplier_id": 1 }, { unique: true })
db.suppliers.createIndex({ "contact.email": 1 })
db.suppliers.createIndex({ "status": 1 })
db.suppliers.createIndex({ "company_name": "text" })
```

#### **3. Stock Movements Collection (`stock_movements`)**
```javascript
{
  _id: ObjectId,                    // Primary key
  movement_id: String,              // Unique business identifier (required, indexed)
  product_id: ObjectId,             // Reference to products (required, indexed)
  
  // Movement Details
  movement_type: String,            // "inbound", "outbound", "adjustment", "transfer"
  quantity: Number,                 // Quantity moved (required, can be negative for outbound)
  unit_cost: Number,                // Cost per unit (required for inbound, >= 0)
  total_value: Number,              // Calculated: quantity * unit_cost
  
  // Stock Levels (snapshot at time of movement)
  stock_before: Number,             // Stock level before movement
  stock_after: Number,              // Stock level after movement (calculated)
  
  // Transaction Context
  reference_type: String,           // "purchase_order", "sale", "adjustment", "transfer"
  reference_id: ObjectId,           // Reference to related document
  reason_code: String,              // Standard reason codes
  reason_description: String,       // Detailed reason (max 500 chars)
  
  // Location & Batch Information
  warehouse_location: String,       // Location within warehouse
  lot_number: String,               // Lot/batch number (optional)
  expiration_date: Date,            // For perishable items (optional)
  
  // Metadata
  timestamp: Date,                  // Movement timestamp (required, indexed)
  processed_by: ObjectId,           // User who processed (required)
  approved_by: ObjectId,            // Approval user (for adjustments)
  status: String,                   // "pending", "completed", "cancelled"
  created_at: Date,                 // Auto-generated
  notes: String                     // Additional notes (max 500 chars)
}

// Indexes
db.stock_movements.createIndex({ "movement_id": 1 }, { unique: true })
db.stock_movements.createIndex({ "product_id": 1, "timestamp": -1 })
db.stock_movements.createIndex({ "timestamp": -1 })
db.stock_movements.createIndex({ "movement_type": 1, "timestamp": -1 })
db.stock_movements.createIndex({ "reference_type": 1, "reference_id": 1 })
```

#### **4. Purchase Orders Collection (`purchase_orders`)**
```javascript
{
  _id: ObjectId,                    // Primary key
  order_number: String,             // Unique PO number (required, indexed)
  supplier_id: ObjectId,            // Reference to suppliers (required, indexed)
  
  // Order Status & Dates
  status: String,                   // "draft", "sent", "acknowledged", "shipped", "received", "cancelled"
  order_date: Date,                 // Order creation date (required)
  expected_delivery_date: Date,     // Expected delivery (required)
  actual_delivery_date: Date,       // Actual delivery (optional)
  
  // Line Items
  items: [{
    product_id: ObjectId,           // Reference to products (required)
    quantity_ordered: Number,       // Quantity ordered (required, > 0)
    quantity_received: Number,      // Quantity received (default: 0)
    unit_cost: Number,              // Cost per unit (required, >= 0)
    line_total: Number,             // Calculated: quantity_ordered * unit_cost
    notes: String                   // Line item notes (max 200 chars)
  }],
  
  // Financial Summary
  subtotal: Number,                 // Sum of all line totals
  tax_amount: Number,               // Tax amount (default: 0)
  shipping_cost: Number,            // Shipping cost (default: 0)
  total_amount: Number,             // Calculated: subtotal + tax + shipping
  currency: String,                 // Currency code (default: "USD")
  
  // Shipping Information
  shipping_address: {
    name: String,                   // Recipient name
    street: String,                 // Street address
    city: String,                   // City
    state: String,                  // State/Province
    postal_code: String,            // ZIP/Postal code
    country: String                 // Country code
  },
  
  // Metadata
  created_by: ObjectId,             // User who created order
  approved_by: ObjectId,            // User who approved order
  received_by: ObjectId,            // User who received order
  created_at: Date,                 // Auto-generated
  updated_at: Date,                 // Auto-updated
  notes: String                     // Order notes (max 1000 chars)
}

// Indexes
db.purchase_orders.createIndex({ "order_number": 1 }, { unique: true })
db.purchase_orders.createIndex({ "supplier_id": 1, "order_date": -1 })
db.purchase_orders.createIndex({ "status": 1, "expected_delivery_date": 1 })
db.purchase_orders.createIndex({ "order_date": -1 })
```

#### **5. Users Collection (`users`)**
```javascript
{
  _id: ObjectId,                    // Primary key
  user_id: String,                  // Unique user identifier (required, indexed)
  username: String,                 // Login username (required, unique, indexed)
  email: String,                    // Email address (required, unique, validated)
  
  // Authentication
  password_hash: String,            // Hashed password (required, bcrypt)
  salt: String,                     // Password salt
  last_login: Date,                 // Last login timestamp
  failed_login_attempts: Number,    // Failed login counter (default: 0)
  account_locked: Boolean,          // Account lock status (default: false)
  
  // Profile Information
  profile: {
    first_name: String,             // First name (required, max 50 chars)
    last_name: String,              // Last name (required, max 50 chars)
    display_name: String,           // Display name (optional)
    phone: String,                  // Phone number (optional)
    department: String,             // Department/Team (optional)
    job_title: String               // Job title (optional)
  },
  
  // Permissions & Access
  role: String,                     // "admin", "manager", "staff", "readonly"
  permissions: [String],            // Granular permissions array
  warehouse_access: [String],       // Warehouse locations user can access
  
  // Preferences
  preferences: {
    timezone: String,               // User timezone (default: "UTC")
    language: String,               // Language preference (default: "en")
    notifications: {
      email: Boolean,               // Email notifications (default: true)
      in_app: Boolean,              // In-app notifications (default: true)
      low_stock_alerts: Boolean     // Low stock alerts (default: true)
    }
  },
  
  // Status & Metadata
  status: String,                   // "active", "inactive", "suspended"
  created_at: Date,                 // Auto-generated
  updated_at: Date,                 // Auto-updated
  created_by: ObjectId,             // User who created this account
  notes: String                     // Admin notes (max 500 chars)
}

// Indexes
db.users.createIndex({ "user_id": 1 }, { unique: true })
db.users.createIndex({ "username": 1 }, { unique: true })
db.users.createIndex({ "email": 1 }, { unique: true })
db.users.createIndex({ "status": 1, "role": 1 })
```

#### **6. Alerts Collection (`alerts`)**
```javascript
{
  _id: ObjectId,                    // Primary key
  alert_id: String,                 // Unique alert identifier (required, indexed)
  alert_type: String,               // "low_stock", "overstock", "expiry_warning", "reorder_suggestion"
  
  // Alert Context
  product_id: ObjectId,             // Related product (optional, indexed)
  supplier_id: ObjectId,            // Related supplier (optional)
  
  // Alert Details
  severity: String,                 // "low", "medium", "high", "critical"
  title: String,                    // Alert title (required, max 200 chars)
  message: String,                  // Alert message (required, max 1000 chars)
  current_value: Number,            // Current metric value (e.g., stock level)
  threshold_value: Number,          // Threshold that triggered alert
  
  // Status & Processing
  status: String,                   // "active", "acknowledged", "resolved", "dismissed"
  acknowledged_by: ObjectId,        // User who acknowledged
  acknowledged_at: Date,            // Acknowledgment timestamp
  resolved_by: ObjectId,            // User who resolved
  resolved_at: Date,                // Resolution timestamp
  
  // Metadata
  created_at: Date,                 // Alert creation time (auto-generated, indexed)
  expires_at: Date,                 // Alert expiration (optional)
  action_required: Boolean,         // Whether action is required (default: false)
  auto_generated: Boolean,          // Whether system-generated (default: true)
  notes: String                     // Resolution notes (max 500 chars)
}

// Indexes
db.alerts.createIndex({ "alert_id": 1 }, { unique: true })
db.alerts.createIndex({ "product_id": 1, "created_at": -1 })
db.alerts.createIndex({ "status": 1, "severity": 1, "created_at": -1 })
db.alerts.createIndex({ "alert_type": 1, "created_at": -1 })
db.alerts.createIndex({ "created_at": -1 })
```

### **Data Validation Rules**

#### **Global Validation Patterns**
```javascript
// Email validation
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

// Phone validation (E.164 format)
const phoneRegex = /^\+[1-9]\d{1,14}$/

// Currency validation (ISO 4217)
const currencyRegex = /^[A-Z]{3}$/

// Product ID format (alphanumeric, 8-20 chars)
const productIdRegex = /^[A-Z0-9]{8,20}$/

// SKU format (alphanumeric with hyphens, 6-30 chars)
const skuRegex = /^[A-Z0-9\-]{6,30}$/
```

#### **Collection-Specific Constraints**
```javascript
// Products validation
db.products.validator = {
  $jsonSchema: {
    required: ["product_id", "name", "category", "sku", "supplier_id", 
               "current_stock", "reorder_threshold", "reorder_quantity", 
               "cost_price", "selling_price"],
    properties: {
      current_stock: { minimum: 0 },
      cost_price: { minimum: 0, multipleOf: 0.01 },
      selling_price: { minimum: 0, multipleOf: 0.01 },
      reorder_threshold: { minimum: 1 },
      reorder_quantity: { minimum: 1 }
    }
  }
}
```

### **Snowflake Data Warehouse Schemas (Analytical Database)**

#### **1. Inventory History Table (`inventory_history`)**
```sql
-- Table: inventory_history
-- Purpose: Store daily or periodic snapshots of inventory levels for trend analysis and historical reporting.
CREATE TABLE inventory_history (
    record_id                   VARCHAR(255) PRIMARY KEY, -- Unique record identifier
    product_id                  VARCHAR(255) NOT NULL,    -- Reference to Products.product_id
    snapshot_date               DATE NOT NULL,            -- Date of the inventory snapshot
    stock_level                 NUMBER(10,2) NOT NULL,    -- Current quantity at snapshot time
    total_value_at_cost         NUMBER(15,2),             -- Total cost value of stock at snapshot
    total_value_at_retail       NUMBER(15,2),             -- Total retail value of stock at snapshot
    reorder_threshold           NUMBER(10,2),             -- Product's reorder threshold at snapshot
    available_stock_percentage  NUMBER(5,2),              -- (available_stock / max_stock_level) * 100
    warehouse_location          VARCHAR(255),             -- Primary warehouse for the stock
    days_since_last_restock     NUMBER(10,0),             -- Days since the last restock activity
    inventory_turnover_rate     NUMBER(8,4),              -- Calculated turnover rate
    overstock_flag              BOOLEAN DEFAULT FALSE,    -- Flag if inventory is overstocked
    understock_flag             BOOLEAN DEFAULT FALSE,    -- Flag if inventory is understocked
    recorded_at                 TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- Timestamp of record creation in Snowflake
);

-- Clustering for query performance on common filter columns
ALTER TABLE inventory_history CLUSTER BY (snapshot_date, product_id);

-- Example Indexes/Constraints (Snowflake uses clustering and auto-indexing; explicit CREATE INDEX is not standard)
-- However, for conceptual completeness, if this were a traditional RDBMS:
-- CREATE INDEX idx_inv_hist_date_prod ON inventory_history(snapshot_date, product_id);
-- CREATE INDEX idx_inv_hist_prod_date ON inventory_history(product_id, snapshot_date);
```

#### **2. Sales Analytics Table (`sales_analytics`)**
```sql
-- Table: sales_analytics
-- Purpose: Aggregate historical sales data for demand forecasting, sales trend analysis, and profitability reporting.
CREATE TABLE sales_analytics (
    sale_record_id              VARCHAR(255) PRIMARY KEY, -- Unique sale record identifier
    product_id                  VARCHAR(255) NOT NULL,    -- Reference to Products.product_id
    sale_date                   DATE NOT NULL,            -- Date of the sale
    sale_timestamp              TIMESTAMP_NTZ NOT NULL,   -- Exact timestamp of sale
    quantity_sold               NUMBER(10,2) NOT NULL,    -- Quantity sold in this transaction
    unit_price_at_sale          NUMBER(10,2) NOT NULL,    -- Unit selling price at the time of sale
    total_revenue_line          NUMBER(15,2) NOT NULL,    -- Total revenue for this line item (quantity * unit_price)
    unit_cost_at_sale           NUMBER(10,2),             -- Unit cost price at the time of sale
    total_cost_of_goods_sold    NUMBER(15,2),             -- Total COGS for this line item
    gross_profit_line           NUMBER(15,2),             -- Gross profit for this line item
    customer_id                 VARCHAR(255),             -- Reference to customer (if applicable)
    sales_channel               VARCHAR(50),              -- e.g., 'online', 'retail', 'wholesale'
    region                      VARCHAR(50),              -- Sales region
    promotion_applied           BOOLEAN DEFAULT FALSE,    -- Flag if a promotion was applied
    promotion_details           VARIANT,                  -- JSON object for promotion details
    loaded_at                   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- Timestamp of data load into Snowflake
);

-- Clustering for efficient time-series and product-based queries
ALTER TABLE sales_analytics CLUSTER BY (sale_date, product_id, sales_channel);
```

#### **3. Demand Forecast Table (`demand_forecast`)**
```sql
-- Table: demand_forecast
-- Purpose: Store AI-generated demand predictions, confidence intervals, and model metadata.
CREATE TABLE demand_forecast (
    forecast_id                 VARCHAR(255) PRIMARY KEY, -- Unique forecast identifier
    product_id                  VARCHAR(255) NOT NULL,    -- Reference to Products.product_id
    forecast_date               DATE NOT NULL,            -- Date when the forecast was generated
    forecast_period_start       DATE NOT NULL,            -- Start date of the forecast period
    forecast_period_end         DATE NOT NULL,            -- End date of the forecast period
    predicted_demand_quantity   NUMBER(10,2) NOT NULL,    -- Predicted total demand for the period
    confidence_interval_lower   NUMBER(10,2),             -- Lower bound of the confidence interval
    confidence_interval_upper   NUMBER(10,2),             -- Upper bound of the confidence interval
    model_name                  VARCHAR(255),             -- Name of the forecasting model used (e.g., 'ARIMA', 'Prophet', 'RandomForest')
    model_version               VARCHAR(50),              -- Version of the model
    accuracy_metric             NUMBER(8,4),              -- Accuracy score (e.g., MAPE, RMSE)
    features_used               VARIANT,                  -- JSON array/object of features used in the prediction
    generated_by_agent_id       VARCHAR(255),             -- ID of the AI agent/process that generated the forecast
    generated_at                TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- Timestamp of forecast generation
);

-- Clustering for efficient access by product and forecast period
ALTER TABLE demand_forecast CLUSTER BY (forecast_date, product_id, forecast_period_start);
```

#### **4. Supplier Performance Table (`supplier_performance`)**
```sql
-- Table: supplier_performance
-- Purpose: Track historical performance metrics of suppliers based on orders, quality, and lead times.
CREATE TABLE supplier_performance (
    performance_record_id       VARCHAR(255) PRIMARY KEY, -- Unique record identifier
    supplier_id                 VARCHAR(255) NOT NULL,    -- Reference to Suppliers.supplier_id
    evaluation_period_start     DATE NOT NULL,            -- Start date of the evaluation period
    evaluation_period_end       DATE NOT NULL,            -- End date of the evaluation period
    on_time_delivery_rate       NUMBER(5,2),              -- Percentage of orders delivered on time (0-100)
    quality_score               NUMBER(5,2),              -- Average quality rating from received goods (1-5)
    average_lead_time_days      NUMBER(10,2),             -- Average actual lead time for orders in period
    order_fulfillment_rate      NUMBER(5,2),              -- Percentage of items fulfilled vs ordered
    total_orders_in_period      NUMBER(10,0),             -- Total number of orders placed in period
    total_value_in_period       NUMBER(15,2),             -- Total monetary value of orders in period
    return_rate                 NUMBER(5,2),              -- Percentage of items returned due to quality/damage
    communication_score         NUMBER(5,2),              -- Rating for supplier communication (1-5)
    notes                       VARCHAR(1000),            -- Any specific notes for this evaluation
    recorded_at                 TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() -- Timestamp of record creation in Snowflake
);

-- Clustering for efficient access by supplier and evaluation period
ALTER TABLE supplier_performance CLUSTER BY (evaluation_period_start, supplier_id);
```

These Snowflake schemas provide a robust foundation for analytical workloads, complementing the operational data in MongoDB Atlas.

## API Specifications (REST Endpoints)

The Flask backend exposes a **RESTful API** for all core functionalities. These endpoints are designed to be consumed by the NLX conversational interface, potential web UIs, and other integrations. All requests and responses are JSON-based, and authentication is handled via JWT tokens.

**Base URL**: `/api` (e.g., `https://your-domain.com/api`)
**Authentication**: Bearer Token (JWT) in `Authorization` header (`Authorization: Bearer <token>`)
**Content-Type**: `application/json` for requests with a body

### 1. Authentication Endpoints

#### `POST /api/auth/login` - User Login
- **Description**: Authenticates a user and returns a JWT token for subsequent API calls.
- **Request Body**:
  ```json
  {
    "username": "johndoe",
    "password": "securepassword123"
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600, // Token expires in 1 hour
    "user": {
      "user_id": "USR001",
      "username": "johndoe",
      "email": "john.doe@example.com",
      "role": "manager"
    }
  }
  ```
- **Response (Error - 401 Unauthorized)**:
  ```json
  {
    "error": "Invalid credentials",
    "message": "Username or password incorrect."
  }
  ```

#### `GET /api/auth/status` - Check Authentication Status
- **Description**: Verifies the validity of the current JWT token and returns user information.
- **Headers**: `Authorization: Bearer <token>`
- **Response (Success - 200 OK)**:
  ```json
  {
    "is_authenticated": true,
    "user": {
      "user_id": "USR001",
      "username": "johndoe",
      "email": "john.doe@example.com",
      "role": "manager"
    },
    "expires_at": "2025-01-26T10:30:00Z"
  }
  ```
- **Response (Error - 401 Unauthorized)**:
  ```json
  {
    "error": "Token invalid or expired",
    "message": "Please log in again."
  }
  ```

### 2. Inventory Management Endpoints

#### `GET /api/products` - Get All Products
- **Description**: Retrieves a paginated list of all products with their current inventory levels. Supports filtering.
- **Query Parameters**:
  - `page` (optional, int, default: 1): Page number for results.
  - `limit` (optional, int, default: 20, max: 100): Number of items per page.
  - `category` (optional, string): Filters products by category.
  - `status` (optional, string, enum: `active`, `discontinued`, `pending`): Filters products by status.
  - `low_stock` (optional, boolean, default: `false`): If `true`, returns only products below their reorder threshold.
  - `supplier_id` (optional, string): Filters products by primary supplier.
- **Headers**: `Authorization: Bearer <token>`
- **Response (Success - 200 OK)**:
  ```json
  {
    "products": [
      {
        "product_id": "PRD-XYZ78901",
        "name": "Industrial Sensor Unit",
        "category": "Electronics",
        "current_stock": 75,
        "available_stock": 70,
        "reorder_threshold": 20,
        "status": "active",
        "unit_cost": 50.00,
        "selling_price": 99.99,
        "supplier_id": "SUP001",
        "updated_at": "2025-01-25T14:30:00Z"
      }
    ],
    "pagination": {
      "total_items": 150,
      "total_pages": 8,
      "current_page": 1,
      "items_per_page": 20,
      "has_next": true,
      "has_prev": false
    }
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid query parameters.

#### `GET /api/products/{product_id}` - Get Product Details
- **Description**: Retrieves detailed information for a single product by its `product_id`.
- **Path Parameters**:
  - `product_id` (string, required): The unique identifier of the product.
- **Headers**: `Authorization: Bearer <token>`
- **Response (Success - 200 OK)**:
  ```json
  {
    "product_id": "PRD-XYZ78901",
    "name": "Industrial Sensor Unit",
    "description": "High-precision sensor for industrial automation.",
    "category": "Electronics",
    "subcategory": "Sensors",
    "sku": "SENS-IND-001",
    "barcode": "0123456789012",
    "supplier_id": "SUP001",
    "pricing": {
      "cost_price": 50.00,
      "selling_price": 99.99,
      "currency": "USD",
      "last_updated": "2025-01-20T10:00:00Z"
    },
    "inventory": {
      "current_stock": 75,
      "reserved_stock": 5,
      "available_stock": 70,
      "reorder_threshold": 20,
      "max_stock_level": 200,
      "stock_unit": "pieces"
    },
    "suppliers": [
      {
        "supplier_id": "SUP001",
        "is_primary": true,
        "lead_time_days": 7,
        "min_order_quantity": 50,
        "cost_per_unit": 48.50
      }
    ],
    "specifications": {
      "weight": 250,
      "dimensions": { "length": 10, "width": 5, "height": 3 },
      "color": "Grey",
      "material": "Stainless Steel"
    },
    "warehouse_location": "A-12-Shelf3-Bin4",
    "status": "active",
    "tags": ["automation", "industrial", "IoT"],
    "created_at": "2024-10-01T08:00:00Z",
    "updated_at": "2025-01-25T14:30:00Z"
  }
  ```
- **Response (Error - 404 Not Found)**: Product not found.

#### `POST /api/products` - Create New Product
- **Description**: Adds a new product to the inventory.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "product_id": "NEWPRD-A1B2C3",
    "name": "New Widget X",
    "description": "A brand new and improved widget.",
    "category": "Tools",
    "subcategory": "Hand Tools",
    "sku": "WIDGET-X-001",
    "barcode": "1234567891234",
    "supplier_id": "SUP002",
    "pricing": {
      "cost_price": 10.50,
      "selling_price": 25.00,
      "currency": "USD"
    },
    "inventory": {
      "current_stock": 0,
      "reorder_threshold": 10,
      "reorder_quantity": 50,
      "max_stock_level": 500
    },
    "suppliers": [
      {
        "supplier_id": "SUP002",
        "is_primary": true,
        "lead_time_days": 10,
        "min_order_quantity": 25,
        "cost_per_unit": 10.00
      }
    ],
    "warehouse_location": "B-05-Shelf1-Bin2",
    "status": "pending",
    "tags": ["new arrival", "tool"]
  }
  ```
- **Response (Success - 201 Created)**:
  ```json
  {
    "message": "Product created successfully",
    "product_id": "NEWPRD-A1B2C3",
    "id": "65b2d7b1a2b3c4d5e6f7g8h9"
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid input data.
- **Response (Error - 409 Conflict)**: `product_id` or `sku` already exists.

#### `PUT /api/products/{product_id}` - Update Product Information
- **Description**: Updates existing product details, including stock levels.
- **Path Parameters**: `product_id` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**: (Partial update; any field in the product schema can be updated)
  ```json
  {
    "inventory": {
      "current_stock": 80,
      "reserved_stock": 0
    },
    "status": "active",
    "last_modified_by": "USR001"
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "message": "Product updated successfully",
    "product_id": "PRD-XYZ78901",
    "updated_fields": ["inventory.current_stock", "inventory.reserved_stock", "status"],
    "updated_at": "2025-01-25T15:00:00Z"
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid input data.
- **Response (Error - 404 Not Found)**: Product not found.

### 3. Supplier Management Endpoints

#### `GET /api/suppliers` - Get All Suppliers
- **Description**: Retrieves a paginated list of all registered suppliers.
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `page` (optional, int, default: 1)
  - `limit` (optional, int, default: 20, max: 100)
  - `status` (optional, string, enum: `active`, `inactive`, `pending`): Filters by supplier status.
  - `preferred` (optional, boolean): If `true`, returns only preferred suppliers.
- **Response (Success - 200 OK)**:
  ```json
  {
    "suppliers": [
      {
        "supplier_id": "SUP001",
        "company_name": "Global Parts Inc.",
        "display_name": "GPI",
        "contact": { "email": "info@globalparts.com", "phone": "+15551112222" },
        "status": "active",
        "preferred": true,
        "rating": 4.5
      }
    ],
    "pagination": {
      "total_items": 50,
      "total_pages": 3,
      "current_page": 1,
      "items_per_page": 20
    }
  }
  ```

#### `GET /api/suppliers/{supplier_id}` - Get Supplier Details
- **Description**: Retrieves detailed information for a single supplier.
- **Path Parameters**: `supplier_id` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Response (Success - 200 OK)**:
  ```json
  {
    "supplier_id": "SUP001",
    "company_name": "Global Parts Inc.",
    "display_name": "GPI",
    "contact": {
      "primary_contact": "Jane Doe",
      "email": "info@globalparts.com",
      "phone": "+15551112222",
      "website": "https://globalparts.com"
    },
    "address": {
      "street": "100 Manufacturing Way",
      "city": "Industrial City",
      "state": "CA",
      "postal_code": "90001",
      "country": "USA"
    },
    "business_info": {
      "tax_id": "TAX12345",
      "payment_terms": 30,
      "currency": "USD",
      "lead_time_days": 5,
      "minimum_order_value": 500.00
    },
    "performance": {
      "reliability_score": 92,
      "average_lead_time": 4.8,
      "on_time_delivery_rate": 98.5,
      "quality_rating": 4.5,
      "total_orders": 120,
      "last_order_date": "2025-01-20T00:00:00Z"
    },
    "status": "active",
    "preferred": true,
    "created_at": "2024-05-15T09:00:00Z",
    "updated_at": "2025-01-25T10:00:00Z"
  }
  ```
- **Response (Error - 404 Not Found)**: Supplier not found.

#### `POST /api/suppliers` - Create New Supplier
- **Description**: Adds a new supplier record.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "supplier_id": "SUP003",
    "company_name": "New Tech Components",
    "display_name": "NTC",
    "contact": {
      "primary_contact": "Alice Wonderland",
      "email": "alice@ntc.com",
      "phone": "+15553334444"
    },
    "address": {
      "street": "789 Innovation Drive",
      "city": "Future Town",
      "state": "TX",
      "postal_code": "78701",
      "country": "USA"
    },
    "business_info": {
      "payment_terms": 45,
      "currency": "USD",
      "lead_time_days": 14,
      "minimum_order_value": 100.00
    },
    "status": "active",
    "preferred": false
  }
  ```
- **Response (Success - 201 Created)**:
  ```json
  {
    "message": "Supplier created successfully",
    "supplier_id": "SUP003",
    "id": "65b2d9e0f1g2h3i4j5k6l7m8"
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid input data.
- **Response (Error - 409 Conflict)**: `supplier_id` or `email` already exists.

### 4. Purchase Order Endpoints

#### `GET /api/orders/purchase` - Get All Purchase Orders
- **Description**: Retrieves a paginated list of purchase orders.
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `page` (optional, int, default: 1)
  - `limit` (optional, int, default: 20, max: 100)
  - `status` (optional, string, enum: `draft`, `sent`, `confirmed`, `shipped`, `received`, `cancelled`): Filters by order status.
  - `supplier_id` (optional, string): Filters by supplier.
  - `start_date` (optional, date, format: YYYY-MM-DD): Filters orders placed on or after this date.
  - `end_date` (optional, date, format: YYYY-MM-DD): Filters orders placed on or before this date.
- **Response (Success - 200 OK)**:
  ```json
  {
    "purchase_orders": [
      {
        "order_number": "PO-2025-001",
        "supplier_id": "SUP001",
        "status": "confirmed",
        "order_date": "2025-01-20T09:00:00Z",
        "expected_delivery_date": "2025-01-27T09:00:00Z",
        "total_amount": 5000.00,
        "currency": "USD",
        "items": [
          {
            "product_id": "PRD-XYZ78901",
            "product_name": "Industrial Sensor Unit",
            "quantity_ordered": 50,
            "unit_cost": 50.00,
            "line_total": 2500.00
          }
        ]
      }
    ],
    "pagination": {
      "total_items": 75,
      "total_pages": 4,
      "current_page": 1
    }
  }
  ```

#### `GET /api/orders/purchase/{order_number}` - Get Purchase Order Details
- **Description**: Retrieves detailed information for a single purchase order.
- **Path Parameters**: `order_number` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Response (Success - 200 OK)**:
  ```json
  {
    "order_number": "PO-2025-001",
    "supplier_id": "SUP001",
    "status": "confirmed",
    "order_date": "2025-01-20T09:00:00Z",
    "expected_delivery_date": "2025-01-27T09:00:00Z",
    "actual_delivery_date": null,
    "total_amount": 5000.00,
    "currency": "USD",
    "items": [
      {
        "product_id": "PRD-XYZ78901",
        "product_name": "Industrial Sensor Unit",
        "quantity_ordered": 50,
        "quantity_received": 0,
        "unit_cost": 50.00,
        "line_total": 2500.00,
        "notes": "Fragile items, handle with care."
      },
      {
        "product_id": "PRD-ABC45678",
        "product_name": "Standard Screws (Pack of 1000)",
        "quantity_ordered": 10,
        "quantity_received": 0,
        "unit_cost": 250.00,
        "line_total": 2500.00
      }
    ],
    "financial": {
      "subtotal": 5000.00,
      "tax_amount": 400.00,
      "shipping_cost": 50.00,
      "total_amount": 5450.00,
      "currency": "USD"
    },
    "shipping_address": {
      "name": "Main Warehouse",
      "street": "123 Warehouse Rd",
      "city": "Warehouseville",
      "state": "GA",
      "postal_code": "30303",
      "country": "USA"
    },
    "created_by": "USR001",
    "approved_by": "USR002",
    "created_at": "2025-01-20T08:50:00Z",
    "updated_at": "2025-01-20T09:05:00Z",
    "notes": "Urgent order for Q1 production."
  }
  ```
- **Response (Error - 404 Not Found)**: Purchase order not found.

#### `POST /api/orders/purchase` - Create New Purchase Order
- **Description**: Creates a new purchase order.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "order_number": "PO-2025-002",
    "supplier_id": "SUP001",
    "order_date": "2025-01-25T16:00:00Z",
    "expected_delivery_date": "2025-02-05T00:00:00Z",
    "status": "draft",
    "items": [
      {
        "product_id": "PRD-XYZ78901",
        "quantity_ordered": 75,
        "unit_cost": 50.00
      }
    ],
    "shipping_address": {
      "name": "Main Warehouse",
      "street": "123 Warehouse Rd",
      "city": "Warehouseville",
      "state": "GA",
      "postal_code": "30303",
      "country": "USA"
    },
    "notes": "Follow-up on sensor unit restock recommendation."
  }
  ```
- **Response (Success - 201 Created)**:
  ```json
  {
    "message": "Purchase order created successfully",
    "order_number": "PO-2025-002",
    "id": "65b2dbd1c2d3e4f5g6h7i8j9"
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid input data.
- **Response (Error - 409 Conflict)**: `order_number` already exists.

#### `PUT /api/orders/purchase/{order_number}` - Update Purchase Order
- **Description**: Updates the status or details of an existing purchase order.
- **Path Parameters**: `order_number` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**: (Partial update)
  ```json
  {
    "status": "shipped",
    "actual_delivery_date": "2025-02-03T10:00:00Z",
    "items": [
      {
        "product_id": "PRD-XYZ78901",
        "quantity_received": 75 // Update received quantity for specific item
      }
    ]
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "message": "Purchase order updated successfully",
    "order_number": "PO-2025-001",
    "updated_fields": ["status", "actual_delivery_date", "items"],
    "updated_at": "2025-02-03T10:30:00Z"
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid input.
- **Response (Error - 404 Not Found)**: Order not found.

### 5. Stock Movement Endpoints

#### `GET /api/stock-movements` - Get All Stock Movements
- **Description**: Retrieves a paginated list of all stock movement records.
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `page` (optional, int, default: 1)
  - `limit` (optional, int, default: 20, max: 100)
  - `product_id` (optional, string): Filters by product.
  - `movement_type` (optional, string, enum: `inbound`, `outbound`, `adjustment`, `transfer`): Filters by type.
  - `start_date` (optional, date): Filters movements on or after this date.
  - `end_date` (optional, date): Filters movements on or before this date.
- **Response (Success - 200 OK)**:
  ```json
  {
    "stock_movements": [
      {
        "movement_id": "MOV-2025-001",
        "product_id": "PRD-XYZ78901",
        "movement_type": "inbound",
        "quantity": 50,
        "timestamp": "2025-01-27T10:00:00Z",
        "reference_type": "purchase_order",
        "reference_id": "PO-2025-001",
        "processed_by": "USR003",
        "notes": "Received partial shipment for PO-2025-001."
      }
    ],
    "pagination": {
      "total_items": 200,
      "total_pages": 10,
      "current_page": 1
    }
  }
  ```

#### `POST /api/stock-movements` - Record New Stock Movement
- **Description**: Records a new stock movement (e.g., receipt, sale, adjustment).
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "product_id": "PRD-XYZ78901",
    "movement_type": "adjustment",
    "quantity": -5, // Decrease stock by 5 units
    "unit_cost": 50.00,
    "reason_code": "damaged_goods",
    "reason_description": "5 units found damaged during quality inspection.",
    "warehouse_location": "A-12-Shelf3-Bin4",
    "processed_by": "USR003",
    "timestamp": "2025-01-28T09:00:00Z",
    "notes": "Adjusted stock due to damaged items."
  }
  ```
- **Response (Success - 201 Created)**:
  ```json
  {
    "message": "Stock movement recorded successfully",
    "movement_id": "MOV-2025-002",
    "new_stock_level": 70,
    "id": "65b2dce2e3f4g5h6i7j8k9l0"
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid input data, e.g., negative quantity for `inbound` or insufficient stock for `outbound`.

### 6. User Management Endpoints

#### `GET /api/users` - Get All Users
- **Description**: Retrieves a paginated list of all system users. (Requires `admin` role)
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `page`, `limit`, `role`, `status` (similar to other list endpoints)
- **Response (Success - 200 OK)**:
  ```json
  {
    "users": [
      {
        "user_id": "USR001",
        "username": "johndoe",
        "email": "john.doe@example.com",
        "profile": { "first_name": "John", "last_name": "Doe" },
        "role": "admin",
        "status": "active",
        "last_login": "2025-01-25T15:30:00Z"
      }
    ],
    "pagination": {
      "total_items": 10,
      "total_pages": 1,
      "current_page": 1
    }
  }
  ```

#### `GET /api/users/{user_id}` - Get User Details
- **Description**: Retrieves detailed information for a single user. (Requires `admin` or self)
- **Path Parameters**: `user_id` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Response (Success - 200 OK)**:
  ```json
  {
    "user_id": "USR001",
    "username": "johndoe",
    "email": "john.doe@example.com",
    "profile": {
      "first_name": "John",
      "last_name": "Doe",
      "display_name": "John Doe",
      "department": "Operations"
    },
    "role": "admin",
    "permissions": ["can_manage_users", "can_view_reports"],
    "status": "active",
    "last_login": "2025-01-25T15:30:00Z",
    "preferences": {
      "language": "en",
      "timezone": "America/New_York",
      "notification_settings": {
        "email_notifications": true,
        "low_stock_alerts": true
      }
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2025-01-25T15:30:00Z"
  }
  ```

#### `POST /api/users` - Create New User
- **Description**: Creates a new user account. (Requires `admin` role)
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "username": "newuser",
    "email": "new.user@example.com",
    "password": "StrongPassword!123",
    "first_name": "New",
    "last_name": "User",
    "role": "staff",
    "department": "Warehouse"
  }
  ```
- **Response (Success - 201 Created)**:
  ```json
  {
    "message": "User created successfully",
    "user_id": "USR004",
    "id": "65b2de3f4g5h6i7j8k9l0m1n"
  }
  ```

#### `PUT /api/users/{user_id}` - Update User Details
- **Description**: Updates an existing user's details. (Requires `admin` or self)
- **Path Parameters**: `user_id` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "profile": {
      "department": "Logistics"
    },
    "status": "inactive"
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "message": "User updated successfully",
    "user_id": "USR004",
    "updated_fields": ["profile.department", "status"],
    "updated_at": "2025-01-25T16:00:00Z"
  }
  ```

### 7. Alerts & Insights Endpoints

#### `GET /api/alerts` - Get All Alerts
- **Description**: Retrieves a paginated list of all active or historical alerts.
- **Headers**: `Authorization: Bearer <token>`
- **Query Parameters**:
  - `page`, `limit`
  - `status` (optional, string, enum: `active`, `acknowledged`, `resolved`, `dismissed`): Filters by alert status.
  - `severity` (optional, string, enum: `low`, `medium`, `high`, `critical`): Filters by severity.
  - `alert_type` (optional, string, enum: `low_stock`, `overstock`, `expiry_warning`, `reorder_suggestion`): Filters by type.
  - `product_id` (optional, string): Filters by related product.
- **Response (Success - 200 OK)**:
  ```json
  {
    "alerts": [
      {
        "alert_id": "ALT-2025-001",
        "alert_type": "low_stock",
        "severity": "high",
        "product_id": "PRD-XYZ78901",
        "title": "Low Stock Alert: Industrial Sensor Unit",
        "message": "Current stock (15) is below reorder threshold (20).",
        "status": "active",
        "created_at": "2025-01-25T12:00:00Z"
      }
    ],
    "pagination": {
      "total_items": 25,
      "total_pages": 2,
      "current_page": 1
    }
  }
  ```

#### `POST /api/alerts/{alert_id}/acknowledge` - Acknowledge Alert
- **Description**: Marks an alert as acknowledged, indicating a user has seen it.
- **Path Parameters**: `alert_id` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "acknowledged_by": "USR001",
    "notes": "Acknowledged. PO for this item is being created."
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "message": "Alert acknowledged successfully",
    "alert_id": "ALT-2025-001",
    "status": "acknowledged",
    "acknowledged_at": "2025-01-25T16:30:00Z"
  }
  ```

#### `POST /api/alerts/{alert_id}/resolve` - Resolve Alert
- **Description**: Marks an alert as resolved, usually after corrective action.
- **Path Parameters**: `alert_id` (string, required)
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "resolved_by": "USR001",
    "resolution_notes": "Stock replenished via PO-2025-002.",
    "resolution_type": "stock_replenished",
    "reference_id": "PO-2025-002"
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "message": "Alert resolved successfully",
    "alert_id": "ALT-2025-001",
    "status": "resolved",
    "resolved_at": "2025-01-28T10:00:00Z"
  }
  ```

### 8. System Endpoints

#### `GET /api/health` - Health Check
- **Description**: Provides a basic health check for the API service.
- **Response (Success - 200 OK)**:
  ```json
  {
    "status": "ok",
    "timestamp": "2025-01-25T16:45:00Z",
    "version": "1.0.0",
    "dependencies": {
      "mongodb": "connected",
      "temporal_sdk": "connected",
      "snowflake": "connected",
      "redis": "connected"
    }
  }
  ```

#### `POST /api/agent/query` - AI Agent Natural Language Query
- **Description**: Allows a frontend or NLX to send a natural language query to the AI agent. The agent processes this using its MCP tools.
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
  ```json
  {
    "query": "Which products are most likely to stock out next month?",
    "user_context": {
      "user_id": "USR001",
      "role": "manager",
      "preferred_warehouse": "WH001"
    }
  }
  ```
- **Response (Success - 200 OK)**:
  ```json
  {
    "answer": "Based on current forecasts, Industrial Sensor Unit and Standard Screws are likely to stock out next month. Consider reordering 100 units of sensors and 50 units of screws by Feb 10th.",
    "structured_data": {
      "product_recommendations": [
        { "product_id": "PRD-XYZ78901", "reorder_qty": 100, "by_date": "2025-02-10", "reason": "High demand forecast" }
      ]
    },
    "confidence_score": 0.95,
    "source_tools_used": ["get_inventory", "forecast_demand", "recommend_restock"],
    "processing_time_ms": 1500
  }
  ```
- **Response (Error - 400 Bad Request)**: Invalid query or context.
- **Response (Error - 500 Internal Server Error)**: AI agent processing error.

---

This section provides a detailed specification for the InventoryPulse REST API endpoints. It covers authentication, core inventory management, supplier and order processes, stock movements, user management, and alerts, along with a dedicated endpoint for AI agent interaction. Each endpoint includes:

*   **HTTP Method and URL path**
*   **Description**
*   **Request Body (with example JSON)**
*   **Response (with example JSON for success and common errors)**
*   **Headers and Query/Path Parameters**

This level of detail should enable frontend and other integration teams to effectively consume the backend services.

## Project Directory Structure and File Organization

This section outlines the recommended directory structure and file organization for the InventoryPulse project. This structure aims to promote modularity, maintainability, and clear separation of concerns for both backend and frontend components.

```
inventory-pulse/
├── .env                           # Environment variables (local development)
├── .gitignore                     # Git ignore file
├── README.md                      # Project setup and overview
├── requirements.txt               # Python dependencies
├── run.py                         # Application entry point
├── setup.py                       # Package setup configuration
├── tests/                         # Unit and integration tests
│   ├── __init__.py
│   ├── unit/
│   │   ├── test_products.py
│   │   └── test_users.py
│   └── integration/
│       ├── test_api.py
│       └── test_temporal_workflows.py
├── backend/                       # Flask backend services
│   ├── __init__.py                # Initializes Flask app
│   ├── app.py                     # Main Flask application instance
│   ├── config.py                  # Application configurations (dev, prod, testing)
│   ├── models/                    # MongoDB ORM/ODM models and schemas
│   │   ├── __init__.py
│   │   ├── product_model.py
│   │   ├── supplier_model.py
│   │   ├── order_model.py
│   │   ├── user_model.py
│   │   └── base_model.py          # Base class for common fields/methods
│   ├── routes/                    # API endpoint definitions (Flask Blueprints)
│   │   ├── __init__.py
│   │   ├── auth_routes.py
│   │   ├── product_routes.py
│   │   ├── supplier_routes.py
│   │   ├── order_routes.py
│   │   ├── user_routes.py
│   │   └── health_routes.py
│   ├── services/                  # Business logic and external integrations
│   │   ├── __init__.py
│   │   ├── auth_service.py
│   │   ├── inventory_service.py   # Handles product/stock logic
│   │   ├── supplier_service.py    # Handles supplier data/external calls
│   │   ├── order_service.py       # Handles PO/sales order logic
│   │   ├── user_service.py
│   │   ├── ai_agent_service.py    # Orchestrates AI agent calls/MCP tools
│   │   └── db_service.py          # Database connection/helper functions
│   ├── utils/                     # Utility functions (helpers, validators, decorators)
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   ├── decorators.py
│   │   ├── jwt_utils.py
│   │   └── errors.py              # Custom exception classes
│   ├── middlewares/               # Custom Flask middlewares
│   │   ├── __init__.py
│   │   └── auth_middleware.py
│   ├── workflows/                 # Temporal workflow definitions
│   │   ├── __init__.py
│   │   ├── inventory_workflows.py # Workflow definitions
│   │   └── activities.py          # Temporal activities
│   ├── agents/                    # AI Agent specific code (if separate process)
│   │   ├── __init__.py
│   │   ├── forecasting_agent.py   # Logic for demand forecasting
│   │   ├── supplier_monitoring_agent.py # Scrapers/API clients
│   │   └── nlx_integration_agent.py # For complex NLX queries/fallback
│   └── templates/                 # Frontend templates (if Flask renders any HTML)
│       └── index.html
├── frontend/                      # React frontend application
│   ├── public/
│   │   ├── index.html
│   │   └── favicon.ico
│   ├── src/
│   │   ├── App.tsx
│   │   ├── index.tsx
│   │   ├── components/            # Reusable UI components
│   │   │   ├── Auth/
│   │   │   │   ├── Login.tsx
│   │   │   │   └── Logout.tsx
│   │   │   ├── Inventory/
│   │   │   │   ├── ProductList.tsx
│   │   │   │   └── ProductDetail.tsx
│   │   │   ├── Orders/
│   │   │   │   ├── OrderList.tsx
│   │   │   │   └── CreateOrder.tsx
│   │   │   ├── Shared/
│   │   │   │   ├── Button.tsx
│   │   │   │   └── Table.tsx
│   │   │   └── Chatbot/
│   │   │       └── ChatWindow.tsx
│   │   ├── pages/                 # Top-level views/pages
│   │   │   ├── Dashboard.tsx
│   │   │   ├── InventoryPage.tsx
│   │   │   ├── OrdersPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   ├── contexts/              # React Context API for global state
│   │   │   └── AuthContext.tsx
│   │   ├── hooks/                 # Custom React hooks
│   │   │   └── useAuth.ts
│   │   ├── api/                   # API client logic
│   │   │   ├── index.ts
│   │   │   └── authApi.ts
│   │   ├── assets/                # Static assets (images, icons)
│   │   │   ├── images/
│   │   │   └── icons/
│   │   ├── styles/                # Global styles, themes
│   │   │   ├── theme.ts
│   │   │   └── index.css
│   │   ├── utils/                 # Frontend utility functions
│   │   │   └── helpers.ts
│   │   └── types/                 # TypeScript type definitions
│   │       └── api.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── webpack.config.js          # Or vite.config.js/CRA default
├── docs/                          # Project documentation
│   ├── api-documentation.md
│   ├── database-schemas.md
│   ├── deployment-guide.md
│   └── architecture.md
└── scripts/                       # Utility scripts
    ├── setup.sh
    ├── deploy.sh
    └── run_etl.py                 # ETL script for Mongo to Snowflake
```

This structured layout ensures a clear separation of concerns, simplifies navigation, and supports independent development and deployment of different components. The `backend/` directory is organized by functionality (models, routes, services) while `frontend/` follows common React project patterns. The `docs/` directory will house all key specification documents, including the API documentation and database schemas we've been working on.

This addresses the project structure weak spot. **Next weak spot** we should tackle: defining exact technology versions and dependencies to ensure a consistent development environment. 

## Deployment and Environment Configuration

This section details the deployment strategy and environment configuration for InventoryPulse across various environments (development, staging, production).

### 1. Environment Variables

All sensitive information and environment-specific configurations will be managed via environment variables. A `.env` file will be used for local development, while production environments will leverage cloud-native secret management services.

**Common Environment Variables (Backend)**:
- `FLASK_APP=app.py`
- `FLASK_ENV=development` | `staging` | `production`
- `SECRET_KEY=<your_flask_secret_key>`
- `MONGO_URI=<your_mongodb_atlas_connection_string>`
- `MONGO_DB_NAME=InventoryPulseDB`
- `JWT_SECRET_KEY=<your_jwt_secret_key>`
- `TEMPORAL_GRPC_ENDPOINT=<temporal_server_address>:7233`
- `TEMPORAL_NAMESPACE=default`
- `SNOWFLAKE_ACCOUNT=<your_snowflake_account>`
- `SNOWFLAKE_USERNAME=<your_snowflake_username>`
- `SNOWFLAKE_PASSWORD=<your_snowflake_password>`
- `SNOWFLAKE_WAREHOUSE=<your_snowflake_warehouse>`
- `SNOWFLAKE_DATABASE=<your_snowflake_database>`
- `SNOWFLAKE_SCHEMA=<your_snowflake_schema>`
- `REDIS_URL=redis://localhost:6379/0` (for Celery broker and caching)
- `CELERY_BROKER_URL=redis://localhost:6379/0`
- `CELERY_RESULT_BACKEND=redis://localhost:6379/0`
- `NLX_API_KEY=<your_nlx_api_key>`
- `MINIMAX_API_KEY=<your_minimax_api_key>`
- `MINIMAX_MODEL=<minimax_model_name>` (e.g., "abab6.5-chat")
- `MINIMAX_BASE_URL=<minimax_api_base_url>`
- `WIZ_API_KEY=<your_wiz_api_key>`
- `LOG_LEVEL=INFO` | `DEBUG` | `WARNING` | `ERROR`

**Common Environment Variables (Frontend)**:
- `REACT_APP_API_BASE_URL=http://localhost:5000/api` (or staging/prod URL)
- `REACT_APP_NLX_WIDGET_ID=<your_nlx_widget_id>`
- `REACT_APP_MINIMAX_ENDPOINT=<minimax_tts_asr_endpoint>`

### 2. Local Development Setup

The application is designed for local development and hackathon deployment:
- **Backend**: Flask application running directly with Python virtual environment
- **Frontend**: React development server running with npm/yarn
- **Database**: Local MongoDB instance or MongoDB Atlas connection
- **Temporal**: Local Temporal server for workflow development
- **Redis**: Local Redis instance for Celery and caching

### 3. Local Environment Setup

**Backend Setup**:
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export MONGO_URI=mongodb://localhost:27017/InventoryPulseDB
# ... other environment variables

# Run the application
python app.py
```

**Frontend Setup**:
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set environment variables
export REACT_APP_API_BASE_URL=http://localhost:5000/api
export REACT_APP_MINIMAX_API_KEY=your_minimax_key

# Run development server
npm start
```

**Required Local Services**:
- **MongoDB**: Install locally or use MongoDB Atlas
- **Redis**: Install locally for Celery broker
- **Temporal Server**: Download and run locally for workflow orchestration

### 4. Hackathon Deployment Strategy

For hackathon demonstration and local development:
- **Backend**: Run Flask development server locally (`python app.py`)
- **Frontend**: Run React development server locally (`npm start`)
- **Database**: Use MongoDB Atlas for persistence or local MongoDB instance
- **AI Services**: Connect directly to MiniMax API for LLM capabilities
- **Temporal**: Run local Temporal server for workflow demonstrations
- **Presentation**: Use localhost URLs for demo (frontend: `http://localhost:3000`, backend: `http://localhost:5000`)

### 5. Development Workflow

For hackathon development:
1.  **Code Development**: Develop features locally with hot reload
2.  **Testing**: Run unit tests locally (`pytest` for backend, `npm test` for frontend)
3.  **Integration**: Test API endpoints with local services
4.  **Demo Preparation**: Ensure all services are running locally for presentation
5.  **Version Control**: Use Git for source code management

**Key Development Commands**:
```bash
# Backend testing
pytest tests/

# Frontend testing  
npm test

# Run all services locally
# Terminal 1: MongoDB (if local)
mongod

# Terminal 2: Redis
redis-server

# Terminal 3: Temporal Server
temporal server start-dev

# Terminal 4: Backend
python app.py

# Terminal 5: Frontend
npm start
```

This deployment configuration is optimized for hackathon development and local demonstration, focusing on simplicity and rapid iteration rather than production scalability. 
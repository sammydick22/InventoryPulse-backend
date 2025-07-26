# InventoryPulse

AI-powered inventory management system designed for small to medium-sized businesses. Provides intelligent demand forecasting, automated stock optimization, and real-time insights through conversational interfaces.

## Features

- 🤖 **AI-Powered Insights**: MiniMax LLM integration for intelligent recommendations
- 📊 **Real-time Analytics**: MongoDB Atlas for operational data, Snowflake for analytics
- 🔄 **Workflow Orchestration**: Temporal for reliable multi-step processes
- 💬 **Conversational UI**: NLX integration for natural language interactions
- 🔒 **Secure Authentication**: JWT-based authentication system
- 📈 **Demand Forecasting**: AI-driven stock level predictions
- 🚨 **Smart Alerts**: Automated low stock and reorder notifications

## Technology Stack

### Backend
- **Python 3.11.7** with **Flask 3.0.3**
- **MongoDB Atlas** (operational database)
- **Snowflake** (data warehouse)
- **Temporal** (workflow orchestration)
- **MiniMax** (LLM for AI features)

### Frontend
- **React 18.2.0** with **TypeScript 5.3.3**
- **Material-UI (MUI) 5.15.5**
- Located in `frontend/` directory

## Quick Start

### Prerequisites

1. **Python 3.11+**
2. **Node.js 18+ and npm** (for frontend)
3. **MongoDB** (local installation or Atlas account)

5. **Temporal** (local server)

### Backend Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd inventory-pulse
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment configuration**
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your actual values
   nano .env
   ```

5. **Start required services**
   ```bash
   # Terminal 1: MongoDB (if local)
   mongod
   
   # Terminal 2: Temporal Server
   temporal server start-dev
   ```

6. **Run the backend**
   ```bash
   python run.py
   ```

   The API will be available at `http://localhost:5000`
   API documentation: `http://localhost:5000/api/docs/`

### Frontend Setup

1. **Navigate to frontend directory**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Set environment variables**
   ```bash
   # Create .env file in frontend directory
   echo "REACT_APP_API_BASE_URL=http://localhost:5000/api" > .env
   ```

4. **Start development server**
   ```bash
   npm start
   ```

   The frontend will be available at `http://localhost:3000`

## Environment Variables

### Required Backend Variables

```bash
# Flask Configuration
FLASK_APP=backend/app.py
FLASK_ENV=development
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=your-jwt-secret

# Database
MONGO_URI=mongodb://localhost:27017/InventoryPulseDB

# MiniMax LLM
MINIMAX_API_KEY=your-minimax-key
MINIMAX_MODEL=abab6.5-chat
```

### Optional Variables

```bash
# Temporal
TEMPORAL_GRPC_ENDPOINT=localhost:7233

# Snowflake (for analytics)
SNOWFLAKE_ACCOUNT=your-account
SNOWFLAKE_USERNAME=your-username
SNOWFLAKE_PASSWORD=your-password

# External Services
NLX_API_KEY=your-nlx-key
WIZ_API_KEY=your-wiz-key
```

## API Documentation

Once the backend is running, visit `http://localhost:5000/api/docs/` for interactive API documentation.

### Key Endpoints

- **Authentication**: `/api/auth/login`, `/api/auth/status`
- **Products**: `/api/products` (CRUD operations)
- **Suppliers**: `/api/suppliers` (supplier management)
- **Orders**: `/api/orders/purchase` (purchase orders)
- **Alerts**: `/api/alerts` (system notifications)
- **Health**: `/api/system/health` (system status)

## Development Guidelines

### Code Structure

```
inventory-pulse/
├── backend/               # Flask backend
│   ├── models/           # MongoDB models
│   ├── routes/           # API endpoints
│   ├── services/         # Business logic
│   ├── utils/            # Utilities
│   └── app.py           # Flask app factory
├── frontend/             # React frontend
├── tests/                # Test files
├── requirements.txt      # Python dependencies
└── run.py               # Application entry point
```

### Running Tests

```bash
# Backend tests
pytest tests/

# Frontend tests
cd frontend && npm test
```

### Database Schema

The application uses MongoDB with the following collections:
- `products` - Inventory items
- `suppliers` - Supplier information
- `purchase_orders` - Purchase orders
- `stock_movements` - Stock movement history
- `users` - System users
- `alerts` - System alerts and notifications

Detailed schema definitions are available in `prompt.md`.

## AI Features

### MiniMax Integration

The system integrates with MiniMax LLM for:
- **Demand Forecasting**: Predict future inventory needs
- **Intelligent Recommendations**: Suggest optimal reorder quantities
- **Natural Language Queries**: Process conversational inventory questions
- **Automated Insights**: Generate actionable business insights

### Example AI Queries

```
"Which products are likely to stock out next month?"
"What's the optimal reorder quantity for industrial sensors?"
"Show me suppliers with delivery issues this quarter"
```

## Deployment

### Development Deployment

For hackathon/demo purposes:
```bash
# Start all services
python run.py          # Backend on :5000
cd frontend && npm start   # Frontend on :3000
```

### Production Considerations

- Use environment-specific configuration
- Set up proper secret management
- Configure MongoDB Atlas and Snowflake
- Implement proper logging and monitoring
- Use reverse proxy (nginx) for production

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Ensure MongoDB is running
   - Check connection string in `.env`



3. **MiniMax API Errors**
   - Verify API key is correct
   - Check API rate limits

4. **Frontend Can't Connect to Backend**
   - Ensure backend is running on port 5000
   - Check CORS configuration
   - Verify `REACT_APP_API_BASE_URL` environment variable

### Logs

Backend logs are structured JSON format. Check console output for detailed error information.

## License

This project is developed for educational and demonstration purposes.

## Support

For questions and support, please refer to the project documentation or create an issue in the repository. 
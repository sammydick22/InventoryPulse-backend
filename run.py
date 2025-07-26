#!/usr/bin/env python3
"""
InventoryPulse Application Entry Point
Run this file to start the Flask development server
"""
import os
import sys

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.app import create_app

if __name__ == '__main__':
    # Create the Flask application
    app = create_app()
    
    # Run the development server
    app.run(
        host='0.0.0.0',
        port=5500,
        debug=True,
        use_reloader=True
    ) 
"""
Run file - entry point for the Flask application.
Usage:
    python run.py
    PORT=8080 python run.py  # Use custom port via environment variable
This imports create_app() from the app package and runs the development server.
"""
import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Read port from environment variable, default to 10000
    port = int(os.getenv('PORT', 10000))
    
    # Run in debug mode for development. Turn off debug in production.
    app.run(debug=True, host='0.0.0.0', port=port)

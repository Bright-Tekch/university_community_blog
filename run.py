"""
Run file - entry point for the Flask application.
Usage:
    python run.py
This imports create_app() from the app package and runs the development server.
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    # Run in debug mode for development. Turn off debug in production.
    app.run(debug=True)

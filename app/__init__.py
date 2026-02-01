"""
App package initializer — creates and configures the Flask app.
This file exposes create_app() for the application factory pattern
and also exposes the 'db' SQLAlchemy object for use in other modules.
"""
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Global extensions (initialized without app)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    """Application factory: create and configure the Flask app."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    # Basic configuration - in production, use environment variables instead
    app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY", "dev-secret-key")
    # SQLite DB file inside the app folder
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'app.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Upload settings
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'images')
    app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB

    # Initialize extensions with app
    db.init_app(app)
    migrate.init_app(app, db)

    # Ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # Import and register blueprints (routes)
    from app.routes import main
    app.register_blueprint(main)

    return app

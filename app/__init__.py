"""
Plain Press Finder Flask Application Factory
"""
import logging
import os
from flask import Flask
from dotenv import load_dotenv

# Silence verbose SQLAlchemy logging (prevents Railway rate limit issues)
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)


def create_app(config=None):
    """
    Flask application factory
    
    Args:
        config: Optional configuration dictionary
        
    Returns:
        Flask application instance
    """
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    
    # Default configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Load custom configuration
    if config:
        app.config.from_mapping(config)
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app


# Create app instance for direct running
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5000)

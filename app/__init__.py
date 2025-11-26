"""
Plain Press Finder Flask Application Factory
"""
import os
from flask import Flask, jsonify
from dotenv import load_dotenv


def create_app(config=None):
    """
    Flask application factory
    """
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    
    # Default configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Load custom configuration
    if config:
        app.config.from_mapping(config)
    
    # Simple ping route (no dependencies)
    @app.route('/ping')
    def ping():
        return jsonify({'status': 'pong'})
    
    # Register blueprints
    from app.routes import main
    app.register_blueprint(main)
    
    return app


# Create app instance for direct running
app = create_app()


if __name__ == '__main__':
    app.run(debug=True, port=5000)

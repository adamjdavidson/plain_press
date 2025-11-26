"""
Plain Press Finder Flask Application Factory
"""
import os
import sys
from flask import Flask, jsonify
from dotenv import load_dotenv

print("=== APP STARTING ===", file=sys.stderr, flush=True)


def create_app(config=None):
    """
    Flask application factory
    """
    print("=== create_app called ===", file=sys.stderr, flush=True)
    
    # Load environment variables
    load_dotenv()
    
    app = Flask(__name__)
    
    # Default configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
    
    # Load custom configuration
    if config:
        app.config.from_mapping(config)
    
    # Add a basic health route directly (no imports)
    @app.route('/ping')
    def ping():
        return jsonify({'status': 'pong'})
    
    # Try to register blueprints with error handling
    try:
        print("=== Importing routes ===", file=sys.stderr, flush=True)
        from app.routes import main
        app.register_blueprint(main)
        print("=== Routes registered ===", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"=== ERROR importing routes: {e} ===", file=sys.stderr, flush=True)
        
        @app.route('/error')
        def show_error():
            return jsonify({'error': str(e)})
    
    return app


# Create app instance for direct running
print("=== Creating app instance ===", file=sys.stderr, flush=True)
app = create_app()
print("=== App instance created ===", file=sys.stderr, flush=True)


if __name__ == '__main__':
    app.run(debug=True, port=5000)

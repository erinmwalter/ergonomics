from flask import Flask
from flask_cors import CORS
import logging
from api.config_controller import config_bp
from api.process_controller import process_bp
from api.analysis_controller import analysis_bp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    CORS(app, origins=["http://localhost:3000"])
    
    app.register_blueprint(process_bp)
    app.register_blueprint(config_bp)
    app.register_blueprint(analysis_bp)
    
    @app.route('/health')
    def health_check():
        return {"status": "healthy", "service": "SOP Monitoring API"}, 200
    
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Endpoint not found"}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {"error": "Internal server error"}, 500
    
    return app

if __name__ == '__main__':
    app = create_app()
    logger.info("Starting SOP Monitoring API server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
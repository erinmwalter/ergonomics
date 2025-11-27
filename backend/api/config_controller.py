from flask import Blueprint, request, jsonify
from database import DatabaseService
import logging
import os
import base64
import uuid

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/api')
db = DatabaseService()

@config_bp.route('/upload-image', methods=['POST'])
def upload_image():
    """Upload and save image file"""
    try:
        data = request.get_json()
        
        if not data or 'imageData' not in data:
            return jsonify({"error": "Missing image data"}), 400
        
        image_data = data['imageData']
        
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        filename = f"{uuid.uuid4()}.jpg"
        
        image_bytes = base64.b64decode(image_data)
        
        images_dir = os.path.join('..', 'frontend', 'public', 'images')
        os.makedirs(images_dir, exist_ok=True)
        
        file_path = os.path.join(images_dir, filename)
        
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        
        logger.info(f"Saved image: {filename}")
        
        return jsonify({
            "filename": filename,
            "path": f"images/{filename}"
        }), 201
        
    except Exception as e:
        logger.error(f"Error uploading image: {e}")
        return jsonify({"error": "Failed to upload image"}), 500

@config_bp.route('/environments', methods=['GET'])
def get_environments():
    """Get all environments"""
    try:
        environments = db.get_environments()
        return jsonify(environments), 200
    except Exception as e:
        logger.error(f"Error fetching environments: {e}")
        return jsonify({"error": "Failed to fetch environments"}), 500

@config_bp.route('/environments/<int:env_id>', methods=['GET'])
def get_environment_by_id(env_id):
    """Get specific environment by ID"""
    try:
        environment = db.get_environment_by_id(env_id)
        if environment:
            return jsonify(environment), 200
        else:
            return jsonify({"error": "Environment not found"}), 404
    except Exception as e:
        logger.error(f"Error fetching environment {env_id}: {e}")
        return jsonify({"error": "Failed to fetch environment"}), 500

@config_bp.route('/environments', methods=['POST'])
def create_environment():
    """Create new environment"""
    try:
        data = request.get_json()
        
        if not all(k in data for k in ('name', 'imagePath', 'createdBy')):
            return jsonify({"error": "Missing required fields"}), 400
        
        env_id = db.create_environment(
            name=data['name'],
            image_path=data['imagePath'],
            created_by=data['createdBy']
        )
        
        environment = db.get_environment_by_id(env_id)
        return jsonify(environment), 201
        
    except Exception as e:
        logger.error(f"Error creating environment: {e}")
        return jsonify({"error": "Failed to create environment"}), 500

@config_bp.route('/environments/<int:env_id>/zones', methods=['GET'])
def get_zones_for_environment(env_id):
    """Get all zones for an environment"""
    try:
        zones = db.get_zones_for_environment(env_id)
        return jsonify(zones), 200
    except Exception as e:
        logger.error(f"Error fetching zones for environment {env_id}: {e}")
        return jsonify({"error": "Failed to fetch zones"}), 500

@config_bp.route('/zones', methods=['POST'])
def create_zone():
    """Create new zone"""
    try:
        data = request.get_json()
        
        required_fields = ['EnvironmentId', 'ZoneName', 'Xstart', 'Ystart', 'Xend', 'Yend', 'Color', 'CreatedBy']
        if not all(k in data for k in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        zone_id = db.create_zone(
            environment_id=data['EnvironmentId'],
            zone_name=data['ZoneName'],
            x_start=data['Xstart'],
            y_start=data['Ystart'],
            x_end=data['Xend'],
            y_end=data['Yend'],
            color=data['Color'],
            created_by=data['CreatedBy']
        )
        
        zone = db.get_zone_by_id(zone_id)
        return jsonify(zone), 201
        
    except Exception as e:
        logger.error(f"Error creating zone: {e}")
        return jsonify({"error": "Failed to create zone"}), 500

@config_bp.route('/zones/<int:zone_id>', methods=['DELETE'])
def delete_zone(zone_id):
    """Delete (soft delete) a zone"""
    try:
        success = db.delete_zone(zone_id)
        if success:
            return jsonify({"message": "Zone deleted successfully"}), 200
        else:
            return jsonify({"error": "Zone not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting zone {zone_id}: {e}")
        return jsonify({"error": "Failed to delete zone"}), 500
    
@config_bp.route('/environments/<int:env_id>/zones', methods=['PUT'])
def update_zones_for_environment(env_id):
    """Update all zones for an environment"""
    try:
        data = request.get_json()
        
        if not data or 'zones' not in data:
            return jsonify({"error": "Missing zones data"}), 400
        
        zones = data['zones']
        
        db.execute_update("UPDATE public.\"Zones\" SET \"IsActive\" = false WHERE \"EnvironmentId\" = %s", (env_id,))
        
        # Create new zones
        for zone in zones:
            if zone.get('Id', 0) > 0:  # Only save zones that don't have temp IDs
                db.create_zone(
                    environment_id=env_id,
                    zone_name=zone['ZoneName'],
                    x_start=zone['Xstart'],
                    y_start=zone['Ystart'],
                    x_end=zone['Xend'],
                    y_end=zone['Yend'],
                    color=zone['Color'],
                    created_by=zone.get('CreatedBy', 'admin')
                )
        
        updated_zones = db.get_zones_for_environment(env_id)
        return jsonify(updated_zones), 200
        
    except Exception as e:
        logger.error(f"Error updating zones for environment {env_id}: {e}")
        return jsonify({"error": "Failed to update zones"}), 500
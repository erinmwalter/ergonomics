from flask import Blueprint, request, jsonify
import logging
from database import DatabaseService

logger = logging.getLogger(__name__)

process_bp = Blueprint('process', __name__, url_prefix='/api')

db = DatabaseService(database="postgres")

@process_bp.route('/environments/<int:env_id>/processes', methods=['GET'])
def get_processes_for_environment(env_id):
    """Get all processes for an environment"""
    try:
        processes = db.get_processes_for_environment(env_id)
        return jsonify(processes), 200
    except Exception as e:
        logger.error(f"Error fetching processes for environment {env_id}: {e}")
        return jsonify({"error": "Failed to fetch processes"}), 500

@process_bp.route('/processes', methods=['POST'])
def create_process():
    """Create new process"""
    try:
        data = request.get_json()
        
        required_fields = ['EnvironmentId', 'ProcessName', 'Description', 'Duration']
        if not all(k in data for k in required_fields):
            return jsonify({"error": "Missing required fields"}), 400
        
        if data['Duration'] <= 0:
            return jsonify({"error": "Duration must be positive"}), 400
        
        process_id = db.create_process(
            environment_id=data['EnvironmentId'],
            process_name=data['ProcessName'],
            description=data['Description'],
            duration=data['Duration'],
            created_by='admin'
        )
        
        process = db.get_process_by_id(process_id)
        return jsonify(process), 201
        
    except Exception as e:
        logger.error(f"Error creating process: {e}")
        return jsonify({"error": "Failed to create process"}), 500

@process_bp.route('/processes/<int:process_id>', methods=['GET'])
def get_process(process_id):
    """Get specific process by ID"""
    try:
        process = db.get_process_by_id(process_id)
        if not process:
            return jsonify({"error": "Process not found"}), 404
        return jsonify(process), 200
    except Exception as e:
        logger.error(f"Error fetching process {process_id}: {e}")
        return jsonify({"error": "Failed to fetch process"}), 500

@process_bp.route('/processes/<int:process_id>', methods=['PUT'])
def update_process(process_id):
    """Update process"""
    try:
        data = request.get_json()
        
        if 'Duration' in data and data['Duration'] <= 0:
            return jsonify({"error": "Duration must be positive"}), 400
        
        success = db.update_process(process_id, **data)
        if not success:
            return jsonify({"error": "Process not found or no changes made"}), 404
        
        process = db.get_process_by_id(process_id)
        return jsonify(process), 200
        
    except Exception as e:
        logger.error(f"Error updating process {process_id}: {e}")
        return jsonify({"error": "Failed to update process"}), 500

@process_bp.route('/processes/<int:process_id>', methods=['DELETE'])
def delete_process(process_id):
    """Delete (soft delete) a process"""
    try:
        success = db.delete_process(process_id)
        if success:
            return jsonify({"message": "Process deleted successfully"}), 200
        else:
            return jsonify({"error": "Process not found"}), 404
    except Exception as e:
        logger.error(f"Error deleting process {process_id}: {e}")
        return jsonify({"error": "Failed to delete process"}), 500

@process_bp.route('/processes/<int:process_id>/steps', methods=['GET'])
def get_process_steps(process_id):
    """Get all steps for a process"""
    try:
        steps = db.get_process_steps(process_id)
        return jsonify(steps), 200
    except Exception as e:
        logger.error(f"Error fetching steps for process {process_id}: {e}")
        return jsonify({"error": "Failed to fetch process steps"}), 500

@process_bp.route('/processes/<int:process_id>/steps', methods=['POST'])
def save_process_steps(process_id):
    """Save/replace all steps for a process"""
    try:
        data = request.get_json()
        
        if 'steps' not in data:
            return jsonify({"error": "Missing 'steps' field"}), 400
        
        steps = data['steps']
        
        required_step_fields = ['StepName', 'TargetZoneId', 'Duration', 'Description']
        for i, step in enumerate(steps):
            if not all(k in step for k in required_step_fields):
                return jsonify({"error": f"Step {i+1} missing required fields"}), 400
            
            if step['Duration'] <= 0:
                return jsonify({"error": f"Step {i+1} duration must be positive"}), 400
        
        updated_steps = db.save_process_steps(process_id, steps)
        return jsonify(updated_steps), 200
        
    except Exception as e:
        logger.error(f"Error saving steps for process {process_id}: {e}")
        return jsonify({"error": "Failed to save process steps"}), 500

@process_bp.route('/processes/health', methods=['GET'])
def process_health():
    """Health check for process endpoints"""
    return jsonify({"status": "healthy", "service": "Process API"}), 200
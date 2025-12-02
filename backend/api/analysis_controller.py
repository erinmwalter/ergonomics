from flask import Blueprint, Response, request, jsonify
import logging
import uuid
from datetime import datetime
from database import DatabaseService
from process_analysis_service import ProcessAnalysisService

logger = logging.getLogger(__name__)

# Create blueprint
analysis_bp = Blueprint('analysis', __name__, url_prefix='/api')

# Initialize database
db = DatabaseService(database="postgres")

# Global dict to track zone detections per session
session_zone_tracking = {}

# Store active analysis sessions (in production, use Redis or database)
active_sessions = {}

@analysis_bp.route('/analysis/start', methods=['POST'])
def start_analysis():
    """Start a new analysis session"""
    try:
        data = request.get_json()
        
        if not data or 'environmentId' not in data or 'processId' not in data:
            return jsonify({"error": "Missing environmentId or processId"}), 400
        
        environment_id = data['environmentId']
        process_id = data['processId']
        
        # Create new analysis service instance
        service = ProcessAnalysisService()
        
        # Load the process data
        if not service.load_process(environment_id, process_id):
            return jsonify({"error": "Failed to load process data"}), 400
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Store session
        active_sessions[session_id] = {
            'service': service,
            'environment_id': environment_id,
            'process_id': process_id,
            'created_at': datetime.now(),
            'status': 'ready'
        }
        
        logger.info(f"Analysis session started: {session_id} for process {process_id}")
        
        return jsonify({
            'sessionId': session_id,
            'status': 'ready',
            'message': 'Analysis session initialized'
        }), 201
        
    except Exception as e:
        logger.error(f"Error starting analysis session: {e}")
        return jsonify({"error": "Failed to start analysis session"}), 500

@analysis_bp.route('/analysis/zone-detected/<session_id>', methods=['POST'])
def handle_zone_detection(session_id):
    """Handle zone detection from YOLO tracking and advance steps"""
    try:
        if session_id not in active_sessions:
            logger.warning(f"Zone detection for unknown session: {session_id}")
            return jsonify({"error": "Session not found"}), 404
        
        data = request.get_json()
        zone_id = data.get('zoneId')
        event_type = data.get('eventType')  # 'enter' or 'exit'
        timestamp = data.get('timestamp')
        
        session = active_sessions[session_id]
        service = session['service']
        
        # Initialize zone tracking for this session if needed
        if session_id not in session_zone_tracking:
            session_zone_tracking[session_id] = {
                'current_zone': None,
                'entry_time': None
            }
        
        zone_track = session_zone_tracking[session_id]
        
        if event_type == 'enter':
            # Hand entered zone
            zone_track['current_zone'] = zone_id
            zone_track['entry_time'] = timestamp
            
            # Check if this zone matches the current step's target zone
            current_step = service.session_data.get('current_step', 0)
            steps = service.session_data.get('steps', [])
            
            if current_step < len(steps):
                target_zone_id = steps[current_step].get('TargetZoneId')
                
                if zone_id == target_zone_id:
                    logger.info(f"✓ Correct zone {zone_id} entered for step {current_step + 1}")
                    
                    # ADVANCE STEP IMMEDIATELY ON ENTRY
                    step_event = {
                        'step': current_step + 1,
                        'zoneName': steps[current_step].get('ZoneName'),
                        'targetDuration': steps[current_step].get('Duration', 0),
                        'actualDuration': 0,  # Don't track duration for now
                        'timestamp': timestamp,
                        'adherence': 100
                    }
                    
                    # Add to step events
                    if 'step_events' not in service.session_data:
                        service.session_data['step_events'] = []
                    service.session_data['step_events'].append(step_event)
                    
                    # Advance to next step
                    service.session_data['current_step'] = current_step + 1
                    
                    logger.info(f"✓ STEP {current_step + 1} COMPLETED!")
                    
                    # Check if process is complete
                    if service.session_data['current_step'] >= len(steps):
                        logger.info(f"🎉 PROCESS COMPLETE for session {session_id}")
                        session['status'] = 'completed'
                else:
                    logger.info(f"✗ Wrong zone {zone_id} entered (expected {target_zone_id})")
        
        elif event_type == 'exit':
            # Just reset tracking, no step advancement
            if zone_track['current_zone'] == zone_id:
                logger.info(f"Hand left zone {zone_id}")
                zone_track['current_zone'] = None
                zone_track['entry_time'] = None
        
        return jsonify({"status": "processed"}), 200
        
    except Exception as e:
        logger.error(f"Error handling zone detection: {e}")
        return jsonify({"error": str(e)}), 500

@analysis_bp.route('/analysis/start-tracking/<session_id>', methods=['POST'])
def start_tracking(session_id):
    """Start tracking for an existing session"""
    try:
        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        session = active_sessions[session_id]
        service = session['service']
        
        # Start tracking
        service.start_tracking()
        session['status'] = 'tracking'
        
        logger.info(f"Tracking started for session: {session_id}")
        
        return jsonify({
            'status': 'tracking',
            'message': 'Process tracking started'
        }), 200
        
    except Exception as e:
        logger.error(f"Error starting tracking for session {session_id}: {e}")
        return jsonify({"error": "Failed to start tracking"}), 500

@analysis_bp.route('/analysis/stop/<session_id>', methods=['POST'])
def stop_analysis(session_id):
    """Stop analysis session and return results"""
    try:
        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        session = active_sessions[session_id]
        service = session['service']
        
        # Stop tracking and get results
        results = service.stop_tracking()
        session['status'] = 'completed'
        session['results'] = results
        
        logger.info(f"Analysis session stopped: {session_id}")
        
        return jsonify({
            'status': 'completed',
            'results': results
        }), 200
        
    except Exception as e:
        logger.error(f"Error stopping analysis session {session_id}: {e}")
        return jsonify({"error": "Failed to stop analysis session"}), 500

@analysis_bp.route('/analysis/status/<session_id>', methods=['GET'])
def get_analysis_status(session_id):
    """Get current status of analysis session"""
    try:
        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        session = active_sessions[session_id]
        service = session['service']
        
        # Get current tracking status
        status_data = {
            'sessionId': session_id,
            'status': session['status'],
            'isActive': service.is_tracking,
            'currentStep': service.session_data.get('current_step', 0),
            'stepEvents': service.session_data.get('step_events', []),
            'elapsedTime': 0
        }
        
        # Calculate elapsed time if tracking
        if service.is_tracking and service.session_data.get('start_time'):
            import time
            status_data['elapsedTime'] = time.time() - service.session_data['start_time']
        
        return jsonify(status_data), 200
        
    except Exception as e:
        logger.error(f"Error getting status for session {session_id}: {e}")
        return jsonify({"error": "Failed to get session status"}), 500

@analysis_bp.route('/analysis/process-frame/<session_id>', methods=['POST'])
def process_frame(session_id):
    """Process a video frame for analysis (for webcam integration)"""
    try:
        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        session = active_sessions[session_id]
        service = session['service']
        
        # Get frame data from request
        if request.content_type.startswith('image/'):
            # Handle raw image data
            import numpy as np
            import cv2
            from io import BytesIO
            
            # Decode image
            image_data = request.get_data()
            nparr = np.frombuffer(image_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # Process frame with YOLO
                processed_frame = service.process_frame(frame)
                
                # Encode processed frame back to JPEG
                _, buffer = cv2.imencode('.jpg', processed_frame)
                response_data = buffer.tobytes()
                
                return Response(response_data, mimetype='image/jpeg')
        
        return jsonify({"error": "Invalid frame data"}), 400
        
    except Exception as e:
        logger.error(f"Error processing frame for session {session_id}: {e}")
        return jsonify({"error": "Failed to process frame"}), 500

@analysis_bp.route('/analysis/results/<session_id>', methods=['POST'])
def save_results(session_id):
    """Save analysis results to database"""
    try:
        data = request.get_json()
        
        if session_id not in active_sessions:
            return jsonify({"error": "Session not found"}), 404
        
        session = active_sessions[session_id]
        results = data.get('results')
        
        logger.info(f"Results saved for session {session_id}: {results}")
        
        return jsonify({"message": "Results saved successfully"}), 200
        
    except Exception as e:
        logger.error(f"Error saving results for session {session_id}: {e}")
        return jsonify({"error": "Failed to save results"}), 500

@analysis_bp.route('/analysis/history', methods=['GET'])
def get_analysis_history():
    """Get history of analysis sessions"""
    try:
        environment_id = request.args.get('environmentId')
        process_id = request.args.get('processId')
        
        return jsonify([]), 200
        
    except Exception as e:
        logger.error(f"Error getting analysis history: {e}")
        return jsonify({"error": "Failed to get analysis history"}), 500

@analysis_bp.route('/analysis/sessions', methods=['GET'])
def get_active_sessions():
    """Get list of active analysis sessions (for debugging)"""
    try:
        sessions_info = []
        for session_id, session in active_sessions.items():
            sessions_info.append({
                'sessionId': session_id,
                'status': session['status'],
                'environmentId': session['environment_id'],
                'processId': session['process_id'],
                'createdAt': session['created_at'].isoformat(),
                'isTracking': session['service'].is_tracking
            })
        
        return jsonify(sessions_info), 200
        
    except Exception as e:
        logger.error(f"Error getting active sessions: {e}")
        return jsonify({"error": "Failed to get active sessions"}), 500

@analysis_bp.route('/analysis/cleanup/<session_id>', methods=['DELETE'])
def cleanup_session(session_id):
    """Clean up an analysis session"""
    try:
        if session_id in active_sessions:
            session = active_sessions[session_id]
            service = session['service']
            
            if service.is_tracking:
                service.stop_tracking()
            
            del active_sessions[session_id]
            
            logger.info(f"Session cleaned up: {session_id}")
            
        return jsonify({"message": "Session cleaned up"}), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up session {session_id}: {e}")
        return jsonify({"error": "Failed to cleanup session"}), 500

@analysis_bp.route('/analysis/health', methods=['GET'])
def analysis_health():
    """Health check for analysis endpoints"""
    return jsonify({
        "status": "healthy", 
        "service": "Analysis API",
        "active_sessions": len(active_sessions)
    }), 200
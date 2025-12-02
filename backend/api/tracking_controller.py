from flask import Blueprint, Response, jsonify, request
import cv2
import numpy as np
import logging
import time

logger = logging.getLogger(__name__)
tracking_bp = Blueprint('tracking', __name__, url_prefix='/api/tracking')

# Try to load YOLO, but don't crash if it's not available
model = None
YOLO_AVAILABLE = False

try:
    from ultralytics import YOLO
    model = YOLO('yolo11n-pose.pt')
    YOLO_AVAILABLE = True
    logger.info("YOLO model loaded successfully")
except ImportError:
    logger.warning("ultralytics not installed. Install with: pip install ultralytics --break-system-packages")
except Exception as e:
    logger.warning(f"Failed to load YOLO model: {e}")

# Skeleton connections for drawing stick figure
SKELETON = [
    [16, 14], [14, 12], [17, 15], [15, 13], [12, 13],  # Face
    [6, 12], [7, 13],  # Shoulders to hips
    [6, 8], [8, 10],  # Left arm
    [7, 9], [9, 11],  # Right arm
    [6, 7],  # Shoulders
    [12, 14], [14, 16],  # Left leg
    [13, 15], [15, 17]   # Right leg
]

# COCO keypoint indices
KEYPOINT_NAMES = [
    'nose', 'left_eye', 'right_eye', 'left_ear', 'right_ear',
    'left_shoulder', 'right_shoulder', 'left_elbow', 'right_elbow',
    'left_wrist', 'right_wrist', 'left_hip', 'right_hip',
    'left_knee', 'right_knee', 'left_ankle', 'right_ankle'
]

LEFT_WRIST_IDX = 9
RIGHT_WRIST_IDX = 10

def draw_pose(img, keypoints, conf_threshold=0.5):
    """Draw stick figure on detected person"""
    for kp in keypoints:
        # Draw keypoints
        for i, (x, y, conf) in enumerate(kp):
            if conf > conf_threshold:
                cv2.circle(img, (int(x), int(y)), 4, (0, 255, 0), -1)
        
        # Draw skeleton connections
        for connection in SKELETON:
            pt1_idx, pt2_idx = connection[0] - 1, connection[1] - 1
            if pt1_idx < len(kp) and pt2_idx < len(kp):
                x1, y1, conf1 = kp[pt1_idx]
                x2, y2, conf2 = kp[pt2_idx]
                
                if conf1 > conf_threshold and conf2 > conf_threshold:
                    cv2.line(img, (int(x1), int(y1)), (int(x2), int(y2)), 
                            (255, 0, 0), 2)
    
    return img

def draw_hand_boxes(img, keypoints, box_size=50, conf_threshold=0.5):
    """Draw boxes around detected wrists (hands)"""
    for kp in keypoints:
        # Left wrist
        if LEFT_WRIST_IDX < len(kp):
            x, y, conf = kp[LEFT_WRIST_IDX]
            if conf > conf_threshold:
                x1 = int(x - box_size // 2)
                y1 = int(y - box_size // 2)
                x2 = int(x + box_size // 2)
                y2 = int(y + box_size // 2)
                cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(img, 'L', (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (0, 255, 255), 2)
        
        # Right wrist
        if RIGHT_WRIST_IDX < len(kp):
            x, y, conf = kp[RIGHT_WRIST_IDX]
            if conf > conf_threshold:
                x1 = int(x - box_size // 2)
                y1 = int(y - box_size // 2)
                x2 = int(x + box_size // 2)
                y2 = int(y + box_size // 2)
                cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 0), 2)
                cv2.putText(img, 'R', (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (255, 255, 0), 2)
    
    return img

def check_hand_in_zone(keypoints, zone, conf_threshold=0.5):
    """Check if either hand is within a zone"""
    for kp in keypoints:
        # Check left wrist
        if LEFT_WRIST_IDX < len(kp):
            x, y, conf = kp[LEFT_WRIST_IDX]
            if conf > conf_threshold:
                if (zone['x'] <= x <= zone['x'] + zone['width'] and 
                    zone['y'] <= y <= zone['y'] + zone['height']):
                    return True, 'left'
        
        # Check right wrist
        if RIGHT_WRIST_IDX < len(kp):
            x, y, conf = kp[RIGHT_WRIST_IDX]
            if conf > conf_threshold:
                if (zone['x'] <= x <= zone['x'] + zone['width'] and 
                    zone['y'] <= y <= zone['y'] + zone['height']):
                    return True, 'right'
    
    return False, None

def draw_zones(img, zones):
    """Draw zones on the image"""
    for zone in zones:
        x, y, w, h = zone['x'], zone['y'], zone['width'], zone['height']
        # Draw zone rectangle
        cv2.rectangle(img, (int(x), int(y)), (int(x + w), int(y + h)), 
                     (0, 255, 0), 2)
        # Draw zone label
        cv2.putText(img, zone['name'], (int(x), int(y) - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    return img

def generate_frames(zones=None, session_id=None):
    """Generate video frames with YOLO pose detection"""
    if not YOLO_AVAILABLE:
        logger.error("YOLO not available - cannot generate frames")
        return
    
    # Try DirectShow backend (CAP_DSHOW) for Windows
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Set resolution to 640x480
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    if not cap.isOpened():
        logger.error("Failed to open webcam")
        return
    
    # Track which zones hands are currently in
    current_zone_detections = {}
    zone_entry_times = {}
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Run YOLOv11 pose detection
            results = model(frame, verbose=False)
            
            # Process keypoints
            keypoints_data = []
            for result in results:
                if result.keypoints is not None:
                    keypoints = result.keypoints.xy.cpu().numpy()
                    confidences = result.keypoints.conf.cpu().numpy()
                    
                    # Combine coordinates with confidences
                    for i in range(len(keypoints)):
                        person_kp = []
                        for j in range(len(keypoints[i])):
                            x, y = keypoints[i][j]
                            conf = confidences[i][j]
                            person_kp.append([x, y, conf])
                        keypoints_data.append(person_kp)
            
            # Draw stick figure
            frame = draw_pose(frame, keypoints_data)
            
            # Draw hand boxes
            frame = draw_hand_boxes(frame, keypoints_data)
            
            # Draw zones if provided
            if zones:
                frame = draw_zones(frame, zones)
                
                # Check hand interactions with zones and LOG them
                for kp in keypoints_data:
                    for zone in zones:
                        in_zone, hand = check_hand_in_zone([kp], zone)
                        zone_id = zone['id']
                        
                        if in_zone:
                            # Highlight zone when hand is detected
                            x, y, w, h = zone['x'], zone['y'], zone['width'], zone['height']
                            cv2.rectangle(frame, (int(x), int(y)), (int(x + w), int(y + h)), 
                                        (0, 0, 255), 3)
                            
                            # Track zone entry
                            if zone_id not in current_zone_detections:
                                current_zone_detections[zone_id] = True
                                zone_entry_times[zone_id] = time.time()
                                logger.info(f"HAND ENTERED ZONE: {zone['name']} (ID: {zone_id})")
                                
                                # TODO: Send this detection to the analysis session
                                # This is where you'd call an endpoint or update session state
                        else:
                            # Hand left zone
                            if zone_id in current_zone_detections:
                                duration = time.time() - zone_entry_times[zone_id]
                                logger.info(f"HAND LEFT ZONE: {zone['name']} (ID: {zone_id}) - Duration: {duration:.2f}s")
                                del current_zone_detections[zone_id]
                                del zone_entry_times[zone_id]
            
            # Encode frame
            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    
    finally:
        cap.release()
        logger.info("Webcam released")

@tracking_bp.route('/stream')
def video_stream():
    """Stream video with YOLO pose detection"""
    # Get zones from query params if provided
    zones = request.args.get('zones')
    zones_list = None
    
    logger.info(f"Stream request received. Zones param: {zones}")
    
    if zones:
        import json
        try:
            zones_list = json.loads(zones)
            logger.info(f"Parsed zones: {zones_list}")
        except Exception as e:
            logger.error(f"Failed to parse zones: {e}")
    
    response = Response(generate_frames(zones_list),
                       mimetype='multipart/x-mixed-replace; boundary=frame')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@tracking_bp.route('/zone-detection', methods=['POST'])
def report_zone_detection():
    """Receive zone detection events from the tracking stream"""
    try:
        data = request.get_json()
        zone_id = data.get('zoneId')
        zone_name = data.get('zoneName')
        event_type = data.get('eventType')  # 'enter' or 'exit'
        duration = data.get('duration')
        
        logger.info(f"Zone detection: {event_type} zone {zone_name} (ID: {zone_id})")
        
        # TODO: Forward this to the analysis session to check if step should advance
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        logger.error(f"Error handling zone detection: {e}")
        return jsonify({"error": str(e)}), 500

@tracking_bp.route('/status')
def tracking_status():
    """Check if tracking is available"""
    cap = cv2.VideoCapture(0)
    available = cap.isOpened()
    cap.release()
    
    return jsonify({
        'available': available and YOLO_AVAILABLE,
        'model_loaded': YOLO_AVAILABLE,
        'webcam_available': available
    })
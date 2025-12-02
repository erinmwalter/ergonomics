import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import defaultdict

model = YOLO('yolo11n-pose.pt')

# Define the zone (center of frame, approximating a paper at 5 feet)
# Adjust these coordinates based on your camera resolution and setup
ZONE = {
    'x': 320,  # Center x (adjust for your resolution)
    'y': 240,  # Center y (adjust for your resolution)
    'width': 100,  # Width of paper zone
    'height': 140  # Height of paper zone (approx 8.5x11 inch ratio)
}

def get_zone_bounds(zone):
    """Calculate zone boundaries"""
    x1 = zone['x'] - zone['width'] // 2
    y1 = zone['y'] - zone['height'] // 2
    x2 = zone['x'] + zone['width'] // 2
    y2 = zone['y'] + zone['height'] // 2
    return x1, y1, x2, y2

def is_hand_in_zone(hand_pos, zone):
    """Check if hand position is within zone boundaries"""
    if hand_pos is None:
        return False
    
    x, y = hand_pos
    x1, y1, x2, y2 = get_zone_bounds(zone)
    
    return x1 <= x <= x2 and y1 <= y <= y2

def get_hand_positions(keypoints, conf_threshold=0.5):
    """Extract hand positions from YOLO keypoints"""
    hands = {'left': None, 'right': None}
    
    for person_kp in keypoints:
        if len(person_kp) > 10:
            left_wrist = person_kp[9]   # Left wrist
            right_wrist = person_kp[10] # Right wrist
            
            if left_wrist[2] > conf_threshold:
                hands['left'] = (int(left_wrist[0]), int(left_wrist[1]))
            if right_wrist[2] > conf_threshold:
                hands['right'] = (int(right_wrist[0]), int(right_wrist[1]))
    
    return hands

def draw_zone(img, zone, color=(255, 255, 0)):
    """Draw the target zone on the image"""
    x1, y1, x2, y2 = get_zone_bounds(zone)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    
    # Add label
    cv2.putText(img, "TARGET ZONE (5ft)", (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Draw center crosshair
    center_x, center_y = zone['x'], zone['y']
    cv2.line(img, (center_x - 10, center_y), (center_x + 10, center_y), color, 1)
    cv2.line(img, (center_x, center_y - 10), (center_x, center_y + 10), color, 1)
    
    return img

def draw_hands(img, hands, zone):
    """Draw hand boxes and check zone intersection"""
    colors = {'left': (0, 255, 0), 'right': (255, 0, 0)}
    box_size = 40
    
    for hand_type, position in hands.items():
        if position is not None:
            x, y = position
            color = colors[hand_type]
            
            # Check if in zone
            in_zone = is_hand_in_zone(position, zone)
            
            # Change color if in zone
            if in_zone:
                color = (0, 255, 255)  # Yellow for in-zone
            
            # Draw bounding box
            cv2.rectangle(img, 
                         (x - box_size, y - box_size),
                         (x + box_size, y + box_size),
                         color, 2)
            
            # Draw center point
            cv2.circle(img, (x, y), 4, color, -1)
            
            # Add label
            label = f"{hand_type.upper()}"
            if in_zone:
                label += " [IN ZONE]"
            
            cv2.putText(img, label, (x - box_size, y - box_size - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return img

def collect_data_session(distance_ft, duration_sec=10):
    """Collect data for a specific distance"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return None
    
    # Get camera resolution and adjust zone center
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ZONE['x'] = width // 2
    ZONE['y'] = height // 2
    
    print(f"\n{'='*60}")
    print(f"COLLECTING DATA FOR {distance_ft} FEET DISTANCE")
    print(f"Duration: {duration_sec} seconds")
    print(f"{'='*60}")
    print("Position yourself and your hand at the target zone.")
    print("Starting in 3 seconds...\n")
    
    time.sleep(3)
    
    data = {
        'distance_ft': distance_ft,
        'total_frames': 0,
        'frames_with_detection': 0,
        'left_hand_in_zone': 0,
        'right_hand_in_zone': 0,
        'left_hand_detected': 0,
        'right_hand_detected': 0,
        'hand_positions': []
    }
    
    start_time = time.time()
    
    while time.time() - start_time < duration_sec:
        ret, frame = cap.read()
        if not ret:
            break
        
        data['total_frames'] += 1
        
        # Run YOLO pose detection
        results = model(frame, verbose=False)
        
        hands_detected = False
        
        for result in results:
            if result.keypoints is not None:
                keypoints = result.keypoints.xy.cpu().numpy()
                confidences = result.keypoints.conf.cpu().numpy()
                
                # Combine coordinates with confidences
                kp_data = []
                for i in range(len(keypoints)):
                    person_kp = []
                    for j in range(len(keypoints[i])):
                        x, y = keypoints[i][j]
                        conf = confidences[i][j]
                        person_kp.append([x, y, conf])
                    kp_data.append(person_kp)
                
                # Get hand positions
                hands = get_hand_positions(kp_data)
                
                # Record data
                if hands['left'] is not None or hands['right'] is not None:
                    hands_detected = True
                    
                if hands['left'] is not None:
                    data['left_hand_detected'] += 1
                    if is_hand_in_zone(hands['left'], ZONE):
                        data['left_hand_in_zone'] += 1
                    data['hand_positions'].append(('left', hands['left']))
                
                if hands['right'] is not None:
                    data['right_hand_detected'] += 1
                    if is_hand_in_zone(hands['right'], ZONE):
                        data['right_hand_in_zone'] += 1
                    data['hand_positions'].append(('right', hands['right']))
                
                # Draw visualizations
                frame = draw_hands(frame, hands, ZONE)
        
        if hands_detected:
            data['frames_with_detection'] += 1
        
        # Draw zone
        frame = draw_zone(frame, ZONE)
        
        # Display countdown and info
        elapsed = time.time() - start_time
        remaining = duration_sec - elapsed
        
        info_text = [
            f"Distance: {distance_ft} feet",
            f"Time remaining: {remaining:.1f}s",
            f"Frames: {data['total_frames']}",
            f"Detections: {data['frames_with_detection']}"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(frame, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30
        
        cv2.imshow('Depth Perception Test', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return data

def print_summary(all_data):
    """Print summary table of all collected data"""
    print("\n" + "="*80)
    print("DEPTH PERCEPTION TEST RESULTS")
    print("="*80)
    
    # Table header
    print(f"\n{'Distance':<12} {'Frames':<10} {'Detections':<12} {'Left In Zone':<15} {'Right In Zone':<15} {'Detection Rate':<15}")
    print("-" * 80)
    
    for data in all_data:
        distance = f"{data['distance_ft']} ft"
        frames = data['total_frames']
        detections = data['frames_with_detection']
        left_zone = data['left_hand_in_zone']
        right_zone = data['right_hand_in_zone']
        
        detection_rate = (detections / frames * 100) if frames > 0 else 0
        left_zone_pct = (left_zone / data['left_hand_detected'] * 100) if data['left_hand_detected'] > 0 else 0
        right_zone_pct = (right_zone / data['right_hand_detected'] * 100) if data['right_hand_detected'] > 0 else 0
        
        print(f"{distance:<12} {frames:<10} {detections:<12} {left_zone} ({left_zone_pct:.1f}%){'':<6} {right_zone} ({right_zone_pct:.1f}%){'':<6} {detection_rate:.1f}%")
    
    print("\n" + "="*80)
    print("\nNOTES:")
    print("- 'Detections' = frames where at least one hand was detected")
    print("- 'In Zone' percentages show how often detected hands were in the target zone")
    print("- Target zone is positioned at 5 feet from camera")
    print("="*80 + "\n")

def main():
    """Main function to run the depth perception experiment"""
    print("="*80)
    print("DEPTH PERCEPTION EXPERIMENT")
    print("="*80)
    print("\nThis experiment will test hand detection at different distances:")
    print("  - 3 feet (closer than target)")
    print("  - 5 feet (at target zone)")
    print("  - 8 feet (farther than target)")
    print("\nFor each distance, you will have 10 seconds to position your hand")
    print("in the target zone area.")
    print("\nPress ENTER to start or 'q' to quit...")
    
    user_input = input()
    if user_input.lower() == 'q':
        return
    
    distances = [3, 5, 8]  # Test distances in feet
    all_data = []
    
    for distance in distances:
        print(f"\n\nPREPARE FOR {distance} FEET TEST")
        print("Position yourself at the marked distance from the camera.")
        print("Press ENTER when ready (or 'q' to skip)...")
        
        user_input = input()
        if user_input.lower() == 'q':
            continue
        
        data = collect_data_session(distance, duration_sec=10)
        if data is not None:
            all_data.append(data)
        
        print(f"\nCompleted {distance}ft test!")
    
    if all_data:
        print_summary(all_data)
        
        # Save results to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"depth_test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("DEPTH PERCEPTION TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for data in all_data:
                f.write(f"Distance: {data['distance_ft']} feet\n")
                f.write(f"  Total Frames: {data['total_frames']}\n")
                f.write(f"  Frames with Detection: {data['frames_with_detection']}\n")
                f.write(f"  Left Hand Detected: {data['left_hand_detected']}\n")
                f.write(f"  Left Hand In Zone: {data['left_hand_in_zone']}\n")
                f.write(f"  Right Hand Detected: {data['right_hand_detected']}\n")
                f.write(f"  Right Hand In Zone: {data['right_hand_in_zone']}\n\n")
        
        print(f"Results saved to: {filename}")
    
    print("\nDepth perception experiment complete!")

if __name__ == "__main__":
    main()

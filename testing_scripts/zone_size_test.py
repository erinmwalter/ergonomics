import cv2
import numpy as np
from ultralytics import YOLO
import time

model = YOLO('yolo11n-pose.pt')

# Define zone sizes (all centered in frame)
ZONE_SIZES = {
    'small': {
        'width': 60,   # Small zone: 60x80 pixels
        'height': 80,
        'description': '60x80 pixels'
    },
    'medium': {
        'width': 100,  # Medium zone: 100x140 pixels
        'height': 140,
        'description': '100x140 pixels'
    },
    'large': {
        'width': 160,  # Large zone: 160x220 pixels
        'height': 220,
        'description': '160x220 pixels'
    }
}

def create_zone(size_name, center_x, center_y):
    """Create a zone with specified size at center position"""
    size_config = ZONE_SIZES[size_name]
    return {
        'x': center_x,
        'y': center_y,
        'width': size_config['width'],
        'height': size_config['height'],
        'size_name': size_name,
        'description': size_config['description']
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
    confidences = {'left': 0.0, 'right': 0.0}
    
    for person_kp in keypoints:
        if len(person_kp) > 10:
            left_wrist = person_kp[9]   # Left wrist
            right_wrist = person_kp[10] # Right wrist
            
            if left_wrist[2] > conf_threshold:
                hands['left'] = (int(left_wrist[0]), int(left_wrist[1]))
                confidences['left'] = left_wrist[2]
            if right_wrist[2] > conf_threshold:
                hands['right'] = (int(right_wrist[0]), int(right_wrist[1]))
                confidences['right'] = right_wrist[2]
    
    return hands, confidences

def draw_zone(img, zone, color=(255, 255, 0)):
    """Draw the target zone on the image"""
    x1, y1, x2, y2 = get_zone_bounds(zone)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    
    # Add label
    label = f"{zone['size_name'].upper()} ZONE ({zone['description']})"
    cv2.putText(img, label, (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Draw center crosshair
    center_x, center_y = zone['x'], zone['y']
    cv2.line(img, (center_x - 10, center_y), (center_x + 10, center_y), color, 1)
    cv2.line(img, (center_x, center_y - 10), (center_x, center_y + 10), color, 1)
    
    return img

def draw_hands(img, hands, confidences, zone):
    """Draw hand boxes with confidence scores"""
    colors = {'left': (0, 255, 0), 'right': (255, 0, 0)}
    box_size = 40
    
    for hand_type, position in hands.items():
        if position is not None:
            x, y = position
            color = colors[hand_type]
            conf = confidences[hand_type]
            
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
            
            # Add label with confidence
            label = f"{hand_type.upper()} ({conf:.2f})"
            if in_zone:
                label += " [IN]"
            
            cv2.putText(img, label, (x - box_size, y - box_size - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return img

def collect_zone_size_data(zone_size_name, center_x, center_y, target_cycles=20):
    """Collect data for a specific zone size"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return None
    
    zone = create_zone(zone_size_name, center_x, center_y)
    
    print(f"\n{'='*70}")
    print(f"COLLECTING DATA FOR {zone_size_name.upper()} ZONE SIZE")
    print(f"{'='*70}")
    print(f"Zone Dimensions: {zone['description']}")
    print(f"Target: {target_cycles} cycles (hand in/out of zone)")
    print("\nInstructions:")
    print("- Stand 5 feet from the camera")
    print("- Move your hand IN and OUT of the zone")
    print("- Press SPACE to record each state change (in/out)")
    print("- Try to be precise with zone boundaries")
    print("- Press 'q' to finish early")
    print("\nStarting in 3 seconds...\n")
    
    time.sleep(3)
    
    data = {
        'zone_size': zone_size_name,
        'zone_dimensions': zone['description'],
        'zone_width': zone['width'],
        'zone_height': zone['height'],
        'cycles_completed': 0,
        'total_frames': 0,
        'frames_with_detection': 0,
        'hand_in_zone_detected': 0,
        'hand_out_zone_detected': 0,
        'hand_in_zone_expected': 0,
        'hand_out_zone_expected': 0,
        'true_positives': 0,   # Hand correctly detected in zone
        'false_negatives': 0,  # Hand not detected in zone when it should be
        'false_positives': 0,  # Hand detected in zone when it shouldn't be
        'true_negatives': 0,   # Hand correctly not detected in zone
        'confidence_in_zone': [],
        'confidence_out_zone': [],
        'edge_cases': 0  # Times when hand is near edge
    }
    
    # State machine for tracking cycles
    current_state = "out"  # Start with hand out of zone
    state_frames = 0
    min_frames_per_state = 30  # Minimum frames to stay in each state
    
    print("Ready! Press SPACE when your hand is OUT of the zone to begin...")
    
    while data['cycles_completed'] < target_cycles:
        ret, frame = cap.read()
        if not ret:
            break
        
        data['total_frames'] += 1
        state_frames += 1
        
        # Run YOLO pose detection
        results = model(frame, verbose=False)
        
        hand_detected_in_zone = False
        hand_detected = False
        max_confidence = 0.0
        
        for result in results:
            if result.keypoints is not None:
                keypoints = result.keypoints.xy.cpu().numpy()
                confidences_raw = result.keypoints.conf.cpu().numpy()
                
                # Combine coordinates with confidences
                kp_data = []
                for i in range(len(keypoints)):
                    person_kp = []
                    for j in range(len(keypoints[i])):
                        x, y = keypoints[i][j]
                        conf = confidences_raw[i][j]
                        person_kp.append([x, y, conf])
                    kp_data.append(person_kp)
                
                # Get hand positions
                detected_hands, confidences = get_hand_positions(kp_data)
                
                # Check if any hand is detected
                if detected_hands['left'] is not None or detected_hands['right'] is not None:
                    hand_detected = True
                    data['frames_with_detection'] += 1
                
                # Check if hand is in zone and get confidence
                for hand_type in ['left', 'right']:
                    if is_hand_in_zone(detected_hands[hand_type], zone):
                        hand_detected_in_zone = True
                        max_confidence = max(max_confidence, confidences[hand_type])
                        
                        # Check if near edge (within 10 pixels of boundary)
                        if detected_hands[hand_type] is not None:
                            x, y = detected_hands[hand_type]
                            x1, y1, x2, y2 = get_zone_bounds(zone)
                            if (abs(x - x1) < 10 or abs(x - x2) < 10 or 
                                abs(y - y1) < 10 or abs(y - y2) < 10):
                                data['edge_cases'] += 1
                
                # Draw visualizations
                frame = draw_hands(frame, detected_hands, confidences, zone)
        
        # Record statistics based on current expected state
        if current_state == "in":
            data['hand_in_zone_expected'] += 1
            if hand_detected_in_zone:
                data['hand_in_zone_detected'] += 1
                data['true_positives'] += 1
                if max_confidence > 0:
                    data['confidence_in_zone'].append(max_confidence)
            else:
                data['false_negatives'] += 1
        else:  # current_state == "out"
            data['hand_out_zone_expected'] += 1
            if hand_detected_in_zone:
                data['false_positives'] += 1
            else:
                data['hand_out_zone_detected'] += 1
                data['true_negatives'] += 1
        
        # Draw zone
        frame = draw_zone(frame, zone)
        
        # Display info
        info_text = [
            f"Zone: {zone_size_name.upper()} ({zone['description']})",
            f"Cycles: {data['cycles_completed']}/{target_cycles}",
            f"Current State: {current_state.upper()}",
            f"State Frames: {state_frames}",
            f"",
            f"Hand Detected: {'YES' if hand_detected else 'NO'}",
            f"In Zone: {'YES' if hand_detected_in_zone else 'NO'}",
            f"Confidence: {max_confidence:.2f}" if max_confidence > 0 else "",
            f"",
            f"Accuracy: {(data['true_positives'] + data['true_negatives'])/data['total_frames']*100:.1f}%" if data['total_frames'] > 0 else "",
            f"",
            f"Press SPACE to toggle state",
            f"Press 'q' to finish"
        ]
        
        y_offset = 30
        for text in info_text:
            if text:  # Skip empty strings
                cv2.putText(frame, text, (10, y_offset),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                y_offset += 25
        
        # Draw state indicator
        width = frame.shape[1]
        state_color = (0, 255, 255) if current_state == "in" else (128, 128, 128)
        cv2.rectangle(frame, (width - 150, 10), (width - 10, 60), state_color, -1)
        cv2.putText(frame, f"STATE: {current_state.upper()}", (width - 145, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        cv2.imshow('Zone Size Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # Toggle state with spacebar
        if key == ord(' ') and state_frames >= min_frames_per_state:
            if current_state == "out":
                current_state = "in"
                print(f"Cycle {data['cycles_completed'] + 1}: Hand IN zone")
            else:
                current_state = "out"
                data['cycles_completed'] += 1
                print(f"Cycle {data['cycles_completed']}: Hand OUT zone - Cycle complete!")
            
            state_frames = 0
        
        # Quit early
        if key == ord('q'):
            print(f"\nStopping early at {data['cycles_completed']} cycles.")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return data

def print_summary(all_data):
    """Print summary table of all collected data"""
    print("\n" + "="*120)
    print("ZONE SIZE TEST RESULTS")
    print("="*120)
    
    # Table header
    print(f"\n{'Zone Size':<12} {'Dimensions':<18} {'Cycles':<8} {'Accuracy':<10} {'True Pos':<10} {'False Neg':<11} {'Avg Conf (In)':<15} {'Edge Cases':<12}")
    print("-" * 120)
    
    for data in all_data:
        zone = data['zone_size']
        dims = data['zone_dimensions']
        cycles = data['cycles_completed']
        
        # Calculate accuracy
        total = data['total_frames']
        correct = data['true_positives'] + data['true_negatives']
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Calculate rates
        tp_rate = (data['true_positives'] / data['hand_in_zone_expected'] * 100) if data['hand_in_zone_expected'] > 0 else 0
        fn_rate = (data['false_negatives'] / data['hand_in_zone_expected'] * 100) if data['hand_in_zone_expected'] > 0 else 0
        
        # Average confidence
        avg_conf = np.mean(data['confidence_in_zone']) if data['confidence_in_zone'] else 0
        
        edge_cases = data['edge_cases']
        
        print(f"{zone:<12} {dims:<18} {cycles:<8} {accuracy:<10.1f}% {tp_rate:<10.1f}% {fn_rate:<11.1f}% {avg_conf:<15.3f} {edge_cases:<12}")
    
    print("\n" + "="*120)
    print("\nDETAILED STATISTICS:")
    print("="*120)
    
    for data in all_data:
        print(f"\n{data['zone_size'].upper()} ZONE ({data['zone_dimensions']}):")
        print(f"  Cycles Completed: {data['cycles_completed']}")
        print(f"  Total Frames: {data['total_frames']}")
        print(f"  Frames with Hand Detection: {data['frames_with_detection']} ({data['frames_with_detection']/data['total_frames']*100:.1f}%)")
        
        print(f"\n  EXPECTED HAND IN ZONE:")
        print(f"    Total Frames: {data['hand_in_zone_expected']}")
        print(f"    Correctly Detected: {data['true_positives']} ({data['true_positives']/data['hand_in_zone_expected']*100:.1f}%)")
        print(f"    Missed (False Neg): {data['false_negatives']} ({data['false_negatives']/data['hand_in_zone_expected']*100:.1f}%)")
        if data['confidence_in_zone']:
            print(f"    Avg Confidence: {np.mean(data['confidence_in_zone']):.3f}")
            print(f"    Min Confidence: {np.min(data['confidence_in_zone']):.3f}")
            print(f"    Max Confidence: {np.max(data['confidence_in_zone']):.3f}")
        
        print(f"\n  EXPECTED HAND OUT OF ZONE:")
        print(f"    Total Frames: {data['hand_out_zone_expected']}")
        print(f"    Correctly Not Detected: {data['true_negatives']} ({data['true_negatives']/data['hand_out_zone_expected']*100:.1f}%)")
        print(f"    Falsely Detected (False Pos): {data['false_positives']} ({data['false_positives']/data['hand_out_zone_expected']*100:.1f}%)")
        
        print(f"\n  OVERALL METRICS:")
        accuracy = (data['true_positives'] + data['true_negatives'])/data['total_frames']*100
        print(f"    Accuracy: {accuracy:.1f}%")
        print(f"    Edge Case Detections: {data['edge_cases']}")
    
    print("\n" + "="*120)
    print("\nCOMPARATIVE ANALYSIS:")
    print("="*120)
    
    # Compare accuracy across zone sizes
    if len(all_data) > 1:
        print("\nAccuracy by Zone Size:")
        for data in all_data:
            accuracy = (data['true_positives'] + data['true_negatives'])/data['total_frames']*100
            print(f"  {data['zone_size']:<12}: {accuracy:.1f}%")
        
        print("\nTrue Positive Rate (Detection when in zone):")
        for data in all_data:
            tp_rate = (data['true_positives']/data['hand_in_zone_expected']*100) if data['hand_in_zone_expected'] > 0 else 0
            print(f"  {data['zone_size']:<12}: {tp_rate:.1f}%")
        
        print("\nAverage Confidence (when in zone):")
        for data in all_data:
            avg_conf = np.mean(data['confidence_in_zone']) if data['confidence_in_zone'] else 0
            print(f"  {data['zone_size']:<12}: {avg_conf:.3f}")
    
    print("\n" + "="*120)
    print("\nNOTES:")
    print("- 'Accuracy' = percentage of frames where zone detection matched expected state")
    print("- 'True Pos' = correctly detected hand in zone when expected")
    print("- 'False Neg' = failed to detect hand in zone when expected")
    print("- 'Edge Cases' = detections within 10 pixels of zone boundary")
    print("- Each cycle = hand moved IN then OUT of zone")
    print("="*120 + "\n")

def main():
    """Main function to run the zone size experiment"""
    print("="*80)
    print("ZONE SIZE EXPERIMENT")
    print("="*80)
    print("\nThis experiment tests how zone size affects detection accuracy:")
    
    for size_name, size_info in ZONE_SIZES.items():
        print(f"  - {size_name.upper()}: {size_info['description']}")
    
    print("\nFor each zone size:")
    print("  - Stand 5 feet from the camera")
    print("  - Move your hand IN and OUT of the zone precisely")
    print("  - Complete 20 cycles (20 times in, 20 times out)")
    print("  - Press SPACE to toggle between IN/OUT states")
    print("\nPress ENTER to start or 'q' to quit...")
    
    user_input = input()
    if user_input.lower() == 'q':
        return
    
    # Get camera to determine center
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    center_x = width // 2
    center_y = height // 2
    cap.release()
    
    print(f"\nCamera resolution: {width}x{height}")
    print(f"Zone center: ({center_x}, {center_y})\n")
    
    zone_sizes = ['small', 'medium', 'large']
    all_data = []
    
    for size_name in zone_sizes:
        print(f"\n\n{'='*80}")
        print(f"PREPARE FOR {size_name.upper()} ZONE TEST")
        print(f"{'='*80}")
        print(f"Zone Dimensions: {ZONE_SIZES[size_name]['description']}")
        print("\nPosition yourself 5 feet from the camera.")
        print("Start with your hand OUT of the zone.")
        print("\nPress ENTER when ready (or 'q' to skip)...")
        
        user_input = input()
        if user_input.lower() == 'q':
            continue
        
        data = collect_zone_size_data(size_name, center_x, center_y, target_cycles=20)
        if data is not None:
            all_data.append(data)
        
        print(f"\nCompleted {size_name} zone test!")
    
    if all_data:
        print_summary(all_data)
        
        # Save results to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"zone_size_test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("ZONE SIZE TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for data in all_data:
                f.write(f"\n{data['zone_size'].upper()} ZONE ({data['zone_dimensions']}):\n")
                f.write(f"  Cycles Completed: {data['cycles_completed']}\n")
                f.write(f"  Total Frames: {data['total_frames']}\n")
                f.write(f"  True Positives: {data['true_positives']}\n")
                f.write(f"  False Negatives: {data['false_negatives']}\n")
                f.write(f"  True Negatives: {data['true_negatives']}\n")
                f.write(f"  False Positives: {data['false_positives']}\n")
                accuracy = (data['true_positives'] + data['true_negatives'])/data['total_frames']*100
                f.write(f"  Accuracy: {accuracy:.1f}%\n")
                if data['confidence_in_zone']:
                    f.write(f"  Avg Confidence (In Zone): {np.mean(data['confidence_in_zone']):.3f}\n")
                f.write(f"  Edge Cases: {data['edge_cases']}\n")
        
        print(f"\nResults saved to: {filename}")
    
    print("\nZone size experiment complete!")

if __name__ == "__main__":
    main()

import cv2
import numpy as np
from ultralytics import YOLO
import time

model = YOLO('yolo11n-pose.pt')

# Zone configurations (will be adjusted based on camera resolution)
ZONE_PLACEMENTS = {
    'center': {
        'description': 'Center of view',
        'position_calc': lambda w, h: (w // 2, h // 2)
    },
    'top': {
        'description': 'Top edge of view',
        'position_calc': lambda w, h: (w // 2, 70)  # 70 pixels from top
    },
    'left': {
        'description': 'Left edge of view',
        'position_calc': lambda w, h: (70, h // 2)  # 70 pixels from left
    },
    'offset': {
        'description': 'Offset position (25% X, 25% Y)',
        'position_calc': lambda w, h: (int(w * 0.25), int(h * 0.25))
    }
}

# Standard zone size for all placements
ZONE_SIZE = {
    'width': 100,
    'height': 140
}

def create_zone(placement_name, width, height):
    """Create a zone at specified placement"""
    placement_config = ZONE_PLACEMENTS[placement_name]
    x, y = placement_config['position_calc'](width, height)
    
    return {
        'x': x,
        'y': y,
        'width': ZONE_SIZE['width'],
        'height': ZONE_SIZE['height'],
        'placement': placement_name,
        'description': placement_config['description']
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
    label = f"{zone['placement'].upper()} ZONE"
    label_y = y1 - 10 if y1 > 30 else y2 + 20
    cv2.putText(img, label, (x1, label_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    
    # Draw center crosshair
    center_x, center_y = zone['x'], zone['y']
    cv2.line(img, (center_x - 10, center_y), (center_x + 10, center_y), color, 1)
    cv2.line(img, (center_x, center_y - 10), (center_x, center_y + 10), color, 1)
    
    # Draw position coordinates
    coord_text = f"({zone['x']}, {zone['y']})"
    cv2.putText(img, coord_text, (x1, y2 + 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
    
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

def collect_zone_placement_data(placement_name, zone, target_cycles=20):
    """Collect data for a specific zone placement"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return None
    
    print(f"\n{'='*70}")
    print(f"COLLECTING DATA FOR {placement_name.upper()} ZONE PLACEMENT")
    print(f"{'='*70}")
    print(f"Zone Position: {zone['description']}")
    print(f"Zone Location: ({zone['x']}, {zone['y']})")
    print(f"Zone Size: {zone['width']}x{zone['height']} pixels")
    print(f"Target: {target_cycles} cycles (hand in/out of zone)")
    print("\nInstructions:")
    print("- Stand 5 feet from the camera")
    print("- Move your hand IN and OUT of the zone")
    print("- Press SPACE to record each state change (in/out)")
    print("- Note: Edge zones may require different body positioning")
    print("- Press 'q' to finish early")
    print("\nStarting in 3 seconds...\n")
    
    time.sleep(3)
    
    data = {
        'placement': placement_name,
        'zone_description': zone['description'],
        'zone_x': zone['x'],
        'zone_y': zone['y'],
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
        'detection_quality': []  # Track overall detection quality
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
        
        # Track overall detection quality
        if hand_detected and max_confidence > 0:
            data['detection_quality'].append(max_confidence)
        
        # Draw zone
        frame = draw_zone(frame, zone)
        
        # Display info
        info_text = [
            f"Placement: {placement_name.upper()}",
            f"Position: {zone['description']}",
            f"Cycles: {data['cycles_completed']}/{target_cycles}",
            f"State: {current_state.upper()}",
            f"",
            f"Hand Detected: {'YES' if hand_detected else 'NO'}",
            f"In Zone: {'YES' if hand_detected_in_zone else 'NO'}",
            f"Confidence: {max_confidence:.2f}" if max_confidence > 0 else "",
            f"",
            f"Accuracy: {(data['true_positives'] + data['true_negatives'])/data['total_frames']*100:.1f}%" if data['total_frames'] > 0 else "",
            f"",
            f"Press SPACE to toggle",
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
        
        cv2.imshow('Zone Placement Test', frame)
        
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
    print("\n" + "="*130)
    print("ZONE PLACEMENT TEST RESULTS")
    print("="*130)
    
    # Table header
    print(f"\n{'Placement':<12} {'Position':<30} {'Cycles':<8} {'Accuracy':<10} {'True Pos':<10} {'False Neg':<11} {'Avg Conf (In)':<15} {'Avg Conf (All)':<15}")
    print("-" * 130)
    
    for data in all_data:
        placement = data['placement']
        position = data['zone_description']
        cycles = data['cycles_completed']
        
        # Calculate accuracy
        total = data['total_frames']
        correct = data['true_positives'] + data['true_negatives']
        accuracy = (correct / total * 100) if total > 0 else 0
        
        # Calculate rates
        tp_rate = (data['true_positives'] / data['hand_in_zone_expected'] * 100) if data['hand_in_zone_expected'] > 0 else 0
        fn_rate = (data['false_negatives'] / data['hand_in_zone_expected'] * 100) if data['hand_in_zone_expected'] > 0 else 0
        
        # Average confidences
        avg_conf_in = np.mean(data['confidence_in_zone']) if data['confidence_in_zone'] else 0
        avg_conf_all = np.mean(data['detection_quality']) if data['detection_quality'] else 0
        
        print(f"{placement:<12} {position:<30} {cycles:<8} {accuracy:<10.1f}% {tp_rate:<10.1f}% {fn_rate:<11.1f}% {avg_conf_in:<15.3f} {avg_conf_all:<15.3f}")
    
    print("\n" + "="*130)
    print("\nDETAILED STATISTICS:")
    print("="*130)
    
    for data in all_data:
        print(f"\n{data['placement'].upper()} PLACEMENT ({data['zone_description']}):")
        print(f"  Zone Location: ({data['zone_x']}, {data['zone_y']})")
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
        if data['detection_quality']:
            print(f"    Overall Avg Confidence: {np.mean(data['detection_quality']):.3f}")
    
    print("\n" + "="*130)
    print("\nCOMPARATIVE ANALYSIS:")
    print("="*130)
    
    if len(all_data) > 1:
        print("\nAccuracy by Zone Placement:")
        for data in all_data:
            accuracy = (data['true_positives'] + data['true_negatives'])/data['total_frames']*100
            print(f"  {data['placement']:<12} ({data['zone_description']:<30}): {accuracy:.1f}%")
        
        print("\nTrue Positive Rate (Detection when in zone):")
        for data in all_data:
            tp_rate = (data['true_positives']/data['hand_in_zone_expected']*100) if data['hand_in_zone_expected'] > 0 else 0
            print(f"  {data['placement']:<12} ({data['zone_description']:<30}): {tp_rate:.1f}%")
        
        print("\nAverage Confidence (when in zone):")
        for data in all_data:
            avg_conf = np.mean(data['confidence_in_zone']) if data['confidence_in_zone'] else 0
            print(f"  {data['placement']:<12} ({data['zone_description']:<30}): {avg_conf:.3f}")
        
        # Find best and worst performing placements
        accuracies = [(data['placement'], (data['true_positives'] + data['true_negatives'])/data['total_frames']*100) 
                     for data in all_data]
        best = max(accuracies, key=lambda x: x[1])
        worst = min(accuracies, key=lambda x: x[1])
        
        print(f"\nBest Performing Placement: {best[0].upper()} ({best[1]:.1f}% accuracy)")
        print(f"Worst Performing Placement: {worst[0].upper()} ({worst[1]:.1f}% accuracy)")
        print(f"Accuracy Difference: {best[1] - worst[1]:.1f}%")
    
    print("\n" + "="*130)
    print("\nNOTES:")
    print("- 'Accuracy' = percentage of frames where zone detection matched expected state")
    print("- 'True Pos' = correctly detected hand in zone when expected")
    print("- 'False Neg' = failed to detect hand in zone when expected")
    print("- 'Avg Conf (In)' = average confidence when hand is in zone")
    print("- 'Avg Conf (All)' = average confidence across all detections")
    print("- Edge placements (top, left) may show different performance than center")
    print("="*130 + "\n")

def main():
    """Main function to run the zone placement experiment"""
    print("="*80)
    print("ZONE PLACEMENT EXPERIMENT")
    print("="*80)
    print("\nThis experiment tests how zone placement affects detection accuracy:")
    print("  - CENTER: Zone in center of camera view")
    print("  - TOP: Zone at top edge of camera view")
    print("  - LEFT: Zone at left edge of camera view")
    print("  - OFFSET: Zone at 25% X, 25% Y position")
    print("\nAll zones are the same size (100x140 pixels)")
    print("\nFor each placement:")
    print("  - Stand 5 feet from the camera")
    print("  - Move your hand IN and OUT of the zone")
    print("  - Complete 20 cycles (20 times in, 20 times out)")
    print("  - Press SPACE to toggle between IN/OUT states")
    print("  - Note: You may need to adjust your position for edge zones")
    print("\nPress ENTER to start or 'q' to quit...")
    
    user_input = input()
    if user_input.lower() == 'q':
        return
    
    # Get camera to determine resolution
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    
    print(f"\nCamera resolution: {width}x{height}")
    
    # Create zones for each placement
    placements = ['center', 'top', 'left', 'offset']
    zones = {name: create_zone(name, width, height) for name in placements}
    
    # Display zone positions
    print("\nZone Positions:")
    for name, zone in zones.items():
        print(f"  {name.upper():<10}: ({zone['x']:4}, {zone['y']:4}) - {zone['description']}")
    
    print()
    
    all_data = []
    
    for placement_name in placements:
        zone = zones[placement_name]
        
        print(f"\n\n{'='*80}")
        print(f"PREPARE FOR {placement_name.upper()} ZONE PLACEMENT TEST")
        print(f"{'='*80}")
        print(f"Zone Position: {zone['description']}")
        print(f"Zone Location: ({zone['x']}, {zone['y']})")
        
        if placement_name == 'top':
            print("\nNote: You may need to raise your hand higher to reach this zone")
        elif placement_name == 'left':
            print("\nNote: You may need to move to the right side of the frame")
        elif placement_name == 'offset':
            print("\nNote: Zone is in upper-left quadrant of view")
        
        print("\nPosition yourself 5 feet from the camera.")
        print("Start with your hand OUT of the zone.")
        print("\nPress ENTER when ready (or 'q' to skip)...")
        
        user_input = input()
        if user_input.lower() == 'q':
            continue
        
        data = collect_zone_placement_data(placement_name, zone, target_cycles=20)
        if data is not None:
            all_data.append(data)
        
        print(f"\nCompleted {placement_name} placement test!")
    
    if all_data:
        print_summary(all_data)
        
        # Save results to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"zone_placement_test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("ZONE PLACEMENT TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Camera Resolution: {width}x{height}\n\n")
            
            for data in all_data:
                f.write(f"\n{data['placement'].upper()} PLACEMENT:\n")
                f.write(f"  Description: {data['zone_description']}\n")
                f.write(f"  Zone Location: ({data['zone_x']}, {data['zone_y']})\n")
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
        
        print(f"\nResults saved to: {filename}")
    
    print("\nZone placement experiment complete!")

if __name__ == "__main__":
    main()

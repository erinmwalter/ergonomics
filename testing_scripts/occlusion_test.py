import cv2
import numpy as np
from ultralytics import YOLO
import time

model = YOLO('yolo11n-pose.pt')

# Define the zone (center of frame)
ZONE = {
    'x': 320,  # Center x (will be adjusted to camera resolution)
    'y': 240,  # Center y (will be adjusted to camera resolution)
    'width': 100,  # Width of target zone
    'height': 140  # Height of target zone
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
    left_conf = 0.0
    right_conf = 0.0
    
    for person_kp in keypoints:
        if len(person_kp) > 10:
            left_wrist = person_kp[9]   # Left wrist
            right_wrist = person_kp[10] # Right wrist
            
            if left_wrist[2] > conf_threshold:
                hands['left'] = (int(left_wrist[0]), int(left_wrist[1]))
                left_conf = left_wrist[2]
            if right_wrist[2] > conf_threshold:
                hands['right'] = (int(right_wrist[0]), int(right_wrist[1]))
                right_conf = right_wrist[2]
    
    return hands, {'left': left_conf, 'right': right_conf}

def draw_zone(img, zone, color=(255, 255, 0)):
    """Draw the target zone on the image"""
    x1, y1, x2, y2 = get_zone_bounds(zone)
    cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
    
    # Add label
    cv2.putText(img, "TARGET ZONE", (x1, y1 - 10),
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
                label += " [IN ZONE]"
            
            cv2.putText(img, label, (x - box_size, y - box_size - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
    
    return img

def collect_occlusion_data(occlusion_type, test_duration=30):
    """Collect data for a specific occlusion type"""
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return None
    
    # Get camera resolution and adjust zone center
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    ZONE['x'] = width // 2
    ZONE['y'] = height // 2
    
    print(f"\n{'='*70}")
    print(f"COLLECTING DATA FOR {occlusion_type.upper()} OCCLUSION")
    print(f"{'='*70}")
    print(f"Duration: {test_duration} seconds")
    
    if occlusion_type == 'body':
        print("\nInstructions:")
        print("- Place your hand in the target zone")
        print("- Occlude it with your own body (torso, other arm, etc.)")
        print("- Move the occlusion in and out multiple times")
        print("- Vary the amount of occlusion")
    elif occlusion_type == 'solid':
        print("\nInstructions:")
        print("- Place your hand in the target zone")
        print("- Use a solid object (book, clipboard, etc.) to occlude it")
        print("- Move the object in and out multiple times")
        print("- Try full and partial occlusion")
    elif occlusion_type == 'translucent':
        print("\nInstructions:")
        print("- Place your hand in the target zone")
        print("- Use a translucent object (plastic sheet, thin fabric, etc.)")
        print("- Move the object in and out multiple times")
        print("- Observe how detection changes with translucency")
    
    print("\nPress 'o' to mark when occlusion is PRESENT")
    print("Press 'c' to mark when occlusion is CLEAR (no occlusion)")
    print("Press 'q' to finish early")
    print("\nStarting in 3 seconds...\n")
    
    time.sleep(3)
    
    data = {
        'occlusion_type': occlusion_type,
        'total_frames': 0,
        'frames_with_detection': 0,
        'frames_occluded': 0,
        'frames_clear': 0,
        'occluded_detected': 0,
        'occluded_not_detected': 0,
        'clear_detected': 0,
        'clear_not_detected': 0,
        'confidence_when_occluded': [],
        'confidence_when_clear': [],
        'hand_positions_occluded': [],
        'hand_positions_clear': []
    }
    
    # State tracking
    current_state = "clear"  # 'occluded' or 'clear'
    
    print(f"Starting! Current state: {current_state.upper()}")
    print("Mark the state as you move the occlusion in and out...\n")
    
    start_time = time.time()
    
    while time.time() - start_time < test_duration:
        ret, frame = cap.read()
        if not ret:
            break
        
        data['total_frames'] += 1
        
        # Run YOLO pose detection
        results = model(frame, verbose=False)
        
        hand_detected = False
        max_confidence = 0.0
        detected_hands = {'left': None, 'right': None}
        confidences = {'left': 0.0, 'right': 0.0}
        
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
                
                # Check if any hand is in zone
                for hand_type in ['left', 'right']:
                    if is_hand_in_zone(detected_hands[hand_type], ZONE):
                        hand_detected = True
                        max_confidence = max(max_confidence, confidences[hand_type])
                
                # Draw visualizations
                frame = draw_hands(frame, detected_hands, confidences, ZONE)
        
        # Record statistics based on current state
        if current_state == "occluded":
            data['frames_occluded'] += 1
            if hand_detected:
                data['occluded_detected'] += 1
                data['confidence_when_occluded'].append(max_confidence)
                # Record position
                for hand_type in ['left', 'right']:
                    if is_hand_in_zone(detected_hands[hand_type], ZONE):
                        data['hand_positions_occluded'].append(detected_hands[hand_type])
            else:
                data['occluded_not_detected'] += 1
        else:  # current_state == "clear"
            data['frames_clear'] += 1
            if hand_detected:
                data['clear_detected'] += 1
                data['confidence_when_clear'].append(max_confidence)
                # Record position
                for hand_type in ['left', 'right']:
                    if is_hand_in_zone(detected_hands[hand_type], ZONE):
                        data['hand_positions_clear'].append(detected_hands[hand_type])
            else:
                data['clear_not_detected'] += 1
        
        if hand_detected:
            data['frames_with_detection'] += 1
        
        # Draw zone
        frame = draw_zone(frame, ZONE)
        
        # Display info
        elapsed = time.time() - start_time
        remaining = test_duration - elapsed
        
        info_text = [
            f"Occlusion: {occlusion_type.upper()}",
            f"Time: {remaining:.1f}s",
            f"State: {current_state.upper()}",
            f"",
            f"Frames: {data['total_frames']}",
            f"Detected: {data['frames_with_detection']}",
            f"",
            f"Occluded: {data['frames_occluded']}",
            f"  Detected: {data['occluded_detected']}",
            f"  Missed: {data['occluded_not_detected']}",
            f"",
            f"Clear: {data['frames_clear']}",
            f"  Detected: {data['clear_detected']}",
            f"  Missed: {data['clear_not_detected']}",
            f"",
            f"Press 'o' = OCCLUDED",
            f"Press 'c' = CLEAR"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(frame, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            y_offset += 25
        
        # Draw state indicator
        state_color = (0, 0, 255) if current_state == "occluded" else (0, 255, 0)
        cv2.rectangle(frame, (width - 180, 10), (width - 10, 60), state_color, -1)
        cv2.putText(frame, f"STATE: {current_state.upper()}", (width - 175, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        cv2.imshow('Occlusion Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # State changes
        if key == ord('o'):
            current_state = "occluded"
            print(f"[{elapsed:.1f}s] State changed to: OCCLUDED")
        elif key == ord('c'):
            current_state = "clear"
            print(f"[{elapsed:.1f}s] State changed to: CLEAR")
        elif key == ord('q'):
            print(f"\nStopping early at {elapsed:.1f}s")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    return data

def print_summary(all_data):
    """Print summary table of all collected data"""
    print("\n" + "="*110)
    print("OCCLUSION TEST RESULTS")
    print("="*110)
    
    # Table header
    print(f"\n{'Occlusion':<15} {'Total':<8} {'Occluded':<10} {'Clear':<10} {'Occl Det':<12} {'Clear Det':<12} {'Avg Conf (O)':<15} {'Avg Conf (C)':<15}")
    print("-" * 110)
    
    for data in all_data:
        occ_type = data['occlusion_type']
        total = data['total_frames']
        occluded = data['frames_occluded']
        clear = data['frames_clear']
        
        # Detection rates
        occ_det_rate = (data['occluded_detected'] / occluded * 100) if occluded > 0 else 0
        clear_det_rate = (data['clear_detected'] / clear * 100) if clear > 0 else 0
        
        # Average confidences
        avg_conf_occ = np.mean(data['confidence_when_occluded']) if data['confidence_when_occluded'] else 0
        avg_conf_clear = np.mean(data['confidence_when_clear']) if data['confidence_when_clear'] else 0
        
        print(f"{occ_type:<15} {total:<8} {occluded:<10} {clear:<10} {occ_det_rate:<12.1f}% {clear_det_rate:<12.1f}% {avg_conf_occ:<15.3f} {avg_conf_clear:<15.3f}")
    
    print("\n" + "="*110)
    print("\nDETAILED STATISTICS:")
    print("="*110)
    
    for data in all_data:
        print(f"\n{data['occlusion_type'].upper()} OCCLUSION:")
        print(f"  Total Frames: {data['total_frames']}")
        print(f"  Frames with Detection: {data['frames_with_detection']} ({data['frames_with_detection']/data['total_frames']*100:.1f}%)")
        
        print(f"\n  OCCLUDED STATE:")
        print(f"    Total Frames: {data['frames_occluded']}")
        print(f"    Detected in Zone: {data['occluded_detected']} ({data['occluded_detected']/data['frames_occluded']*100:.1f}%)" if data['frames_occluded'] > 0 else "    No occluded frames")
        print(f"    Not Detected: {data['occluded_not_detected']} ({data['occluded_not_detected']/data['frames_occluded']*100:.1f}%)" if data['frames_occluded'] > 0 else "")
        if data['confidence_when_occluded']:
            print(f"    Avg Confidence: {np.mean(data['confidence_when_occluded']):.3f}")
            print(f"    Min Confidence: {np.min(data['confidence_when_occluded']):.3f}")
            print(f"    Max Confidence: {np.max(data['confidence_when_occluded']):.3f}")
        
        print(f"\n  CLEAR STATE (No Occlusion):")
        print(f"    Total Frames: {data['frames_clear']}")
        print(f"    Detected in Zone: {data['clear_detected']} ({data['clear_detected']/data['frames_clear']*100:.1f}%)" if data['frames_clear'] > 0 else "    No clear frames")
        print(f"    Not Detected: {data['clear_not_detected']} ({data['clear_not_detected']/data['frames_clear']*100:.1f}%)" if data['frames_clear'] > 0 else "")
        if data['confidence_when_clear']:
            print(f"    Avg Confidence: {np.mean(data['confidence_when_clear']):.3f}")
            print(f"    Min Confidence: {np.min(data['confidence_when_clear']):.3f}")
            print(f"    Max Confidence: {np.max(data['confidence_when_clear']):.3f}")
        
        # Impact analysis
        if data['frames_occluded'] > 0 and data['frames_clear'] > 0:
            detection_drop = ((data['clear_detected']/data['frames_clear']) - 
                             (data['occluded_detected']/data['frames_occluded'])) * 100
            conf_drop = (np.mean(data['confidence_when_clear']) - 
                        np.mean(data['confidence_when_occluded'])) if (data['confidence_when_clear'] and data['confidence_when_occluded']) else 0
            
            print(f"\n  IMPACT OF OCCLUSION:")
            print(f"    Detection Rate Drop: {detection_drop:.1f}%")
            print(f"    Confidence Drop: {conf_drop:.3f}")
    
    print("\n" + "="*110)
    print("\nNOTES:")
    print("- 'Occl Det' = detection rate when hand is occluded")
    print("- 'Clear Det' = detection rate when hand is not occluded")
    print("- 'Avg Conf' = average confidence score for detections")
    print("- Detection rate drop shows impact of occlusion on tracking ability")
    print("="*110 + "\n")

def main():
    """Main function to run the occlusion experiment"""
    print("="*80)
    print("OCCLUSION EXPERIMENT")
    print("="*80)
    print("\nThis experiment tests hand detection with different types of occlusion:")
    print("  - BODY: Occlude hand with your own body (torso, other arm)")
    print("  - SOLID: Occlude hand with solid object (book, clipboard, cardboard)")
    print("  - TRANSLUCENT: Occlude hand with translucent material (plastic, fabric)")
    print("\nFor each test:")
    print("  - Keep your hand in the target zone")
    print("  - Move the occlusion in and out of frame")
    print("  - Press 'o' when occlusion is PRESENT")
    print("  - Press 'c' when occlusion is CLEAR (removed)")
    print("  - Test runs for 30 seconds each")
    print("\nPress ENTER to start or 'q' to quit...")
    
    user_input = input()
    if user_input.lower() == 'q':
        return
    
    occlusion_types = ['body', 'solid', 'translucent']
    all_data = []
    
    for occ_type in occlusion_types:
        print(f"\n\n{'='*80}")
        print(f"PREPARE FOR {occ_type.upper()} OCCLUSION TEST")
        print(f"{'='*80}")
        
        if occ_type == 'body':
            print("\nSetup:")
            print("  - Position yourself in front of camera")
            print("  - Have one hand ready to place in zone")
            print("  - Use your body to create occlusion")
        elif occ_type == 'solid':
            print("\nSetup:")
            print("  - Prepare a solid object (book, clipboard, etc.)")
            print("  - Position yourself in front of camera")
            print("  - Have one hand ready to place in zone")
        elif occ_type == 'translucent':
            print("\nSetup:")
            print("  - Prepare translucent material (plastic sheet, thin fabric)")
            print("  - Position yourself in front of camera")
            print("  - Have one hand ready to place in zone")
        
        print("\nPress ENTER when ready (or 'q' to skip)...")
        
        user_input = input()
        if user_input.lower() == 'q':
            continue
        
        data = collect_occlusion_data(occ_type, test_duration=30)
        if data is not None:
            all_data.append(data)
        
        print(f"\nCompleted {occ_type} occlusion test!")
    
    if all_data:
        print_summary(all_data)
        
        # Save results to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"occlusion_test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("OCCLUSION TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for data in all_data:
                f.write(f"\n{data['occlusion_type'].upper()} OCCLUSION:\n")
                f.write(f"  Total Frames: {data['total_frames']}\n")
                f.write(f"  Frames Occluded: {data['frames_occluded']}\n")
                f.write(f"  Frames Clear: {data['frames_clear']}\n")
                f.write(f"  Detected (Occluded): {data['occluded_detected']}\n")
                f.write(f"  Detected (Clear): {data['clear_detected']}\n")
                f.write(f"  Detection Rate (Occluded): {data['occluded_detected']/data['frames_occluded']*100:.1f}%\n" if data['frames_occluded'] > 0 else "")
                f.write(f"  Detection Rate (Clear): {data['clear_detected']/data['frames_clear']*100:.1f}%\n" if data['frames_clear'] > 0 else "")
                
                if data['confidence_when_occluded']:
                    f.write(f"  Avg Confidence (Occluded): {np.mean(data['confidence_when_occluded']):.3f}\n")
                if data['confidence_when_clear']:
                    f.write(f"  Avg Confidence (Clear): {np.mean(data['confidence_when_clear']):.3f}\n")
        
        print(f"\nResults saved to: {filename}")
    
    print("\nOcclusion experiment complete!")

if __name__ == "__main__":
    main()

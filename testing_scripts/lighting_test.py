import cv2
import numpy as np
from ultralytics import YOLO
import time
from collections import defaultdict

model = YOLO('yolo11n-pose.pt')

# Define the zone (center of frame, approximating target at 5 feet)
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
    cv2.putText(img, "TARGET ZONE", (x1, y1 - 10),
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

def get_brightness(frame):
    """Calculate average brightness of the frame"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return np.mean(gray)

def collect_lighting_data(lighting_condition, target_cycles=20):
    """Collect data for a specific lighting condition"""
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
    print(f"COLLECTING DATA FOR {lighting_condition.upper()} LIGHTING")
    print(f"{'='*60}")
    print(f"Target: {target_cycles} cycles (hand in/out of zone)")
    print("Stand 5 feet from the camera.")
    print("Move your hand IN and OUT of the zone.")
    print("Press SPACE to record each state (in/out).")
    print("Press 'q' to finish early.")
    print("\nStarting in 3 seconds...\n")
    
    time.sleep(3)
    
    data = {
        'lighting_condition': lighting_condition,
        'cycles_completed': 0,
        'total_frames': 0,
        'frames_with_detection': 0,
        'hand_in_zone_detected': 0,
        'hand_out_zone_detected': 0,
        'hand_in_zone_expected': 0,
        'hand_out_zone_expected': 0,
        'brightness_samples': [],
        'false_positives': 0,  # Hand detected in zone when it shouldn't be
        'false_negatives': 0,  # Hand not detected in zone when it should be
        'true_positives': 0,   # Hand correctly detected in zone
        'true_negatives': 0    # Hand correctly not detected in zone
    }
    
    # State machine for tracking cycles
    current_state = "out"  # Start with hand out of zone
    state_frames = 0
    min_frames_per_state = 30  # Minimum frames to stay in each state (about 1 second)
    
    print("Ready! Press SPACE when your hand is OUT of the zone to begin...")
    
    while data['cycles_completed'] < target_cycles:
        ret, frame = cap.read()
        if not ret:
            break
        
        data['total_frames'] += 1
        state_frames += 1
        
        # Record brightness
        brightness = get_brightness(frame)
        data['brightness_samples'].append(brightness)
        
        # Run YOLO pose detection
        results = model(frame, verbose=False)
        
        hand_detected_in_zone = False
        hand_detected = False
        
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
                
                # Check if any hand is detected
                if hands['left'] is not None or hands['right'] is not None:
                    hand_detected = True
                    data['frames_with_detection'] += 1
                
                # Check if hand is in zone
                if is_hand_in_zone(hands['left'], ZONE) or is_hand_in_zone(hands['right'], ZONE):
                    hand_detected_in_zone = True
                
                # Draw visualizations
                frame = draw_hands(frame, hands, ZONE)
        
        # Record statistics based on current expected state
        if current_state == "in":
            data['hand_in_zone_expected'] += 1
            if hand_detected_in_zone:
                data['hand_in_zone_detected'] += 1
                data['true_positives'] += 1
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
        frame = draw_zone(frame, ZONE)
        
        # Display info
        info_text = [
            f"Lighting: {lighting_condition.upper()}",
            f"Cycles: {data['cycles_completed']}/{target_cycles}",
            f"Current State: {current_state.upper()}",
            f"State Frames: {state_frames}",
            f"Brightness: {brightness:.1f}",
            f"",
            f"Hand Detected: {'YES' if hand_detected else 'NO'}",
            f"In Zone: {'YES' if hand_detected_in_zone else 'NO'}",
            f"",
            f"Press SPACE to toggle state",
            f"Press 'q' to finish"
        ]
        
        y_offset = 30
        for text in info_text:
            cv2.putText(frame, text, (10, y_offset),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y_offset += 25
        
        # Draw state indicator
        state_color = (0, 255, 255) if current_state == "in" else (128, 128, 128)
        cv2.rectangle(frame, (width - 150, 10), (width - 10, 60), state_color, -1)
        cv2.putText(frame, f"STATE: {current_state.upper()}", (width - 145, 40),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        cv2.imshow('Lighting Conditions Test', frame)
        
        key = cv2.waitKey(1) & 0xFF
        
        # Toggle state with spacebar (only if enough frames have passed)
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
    print("\n" + "="*100)
    print("LIGHTING CONDITIONS TEST RESULTS")
    print("="*100)
    
    # Table header
    print(f"\n{'Lighting':<12} {'Cycles':<8} {'Avg Bright':<12} {'Detection':<12} {'Accuracy':<10} {'True Pos':<10} {'False Neg':<10} {'False Pos':<10}")
    print("-" * 100)
    
    for data in all_data:
        condition = data['lighting_condition']
        cycles = data['cycles_completed']
        avg_brightness = np.mean(data['brightness_samples']) if data['brightness_samples'] else 0
        
        # Calculate detection rate
        detection_rate = (data['frames_with_detection'] / data['total_frames'] * 100) if data['total_frames'] > 0 else 0
        
        # Calculate accuracy (correct predictions / total predictions)
        total_predictions = data['total_frames']
        correct_predictions = data['true_positives'] + data['true_negatives']
        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0
        
        # Calculate rates
        tp_rate = (data['true_positives'] / data['hand_in_zone_expected'] * 100) if data['hand_in_zone_expected'] > 0 else 0
        fn_rate = (data['false_negatives'] / data['hand_in_zone_expected'] * 100) if data['hand_in_zone_expected'] > 0 else 0
        fp_rate = (data['false_positives'] / data['hand_out_zone_expected'] * 100) if data['hand_out_zone_expected'] > 0 else 0
        
        print(f"{condition:<12} {cycles:<8} {avg_brightness:<12.1f} {detection_rate:<12.1f}% {accuracy:<10.1f}% {tp_rate:<10.1f}% {fn_rate:<10.1f}% {fp_rate:<10.1f}%")
    
    print("\n" + "="*100)
    print("\nDETAILED STATISTICS:")
    print("="*100)
    
    for data in all_data:
        print(f"\n{data['lighting_condition'].upper()} LIGHTING:")
        print(f"  Cycles Completed: {data['cycles_completed']}")
        print(f"  Total Frames: {data['total_frames']}")
        print(f"  Average Brightness: {np.mean(data['brightness_samples']):.1f}")
        print(f"  Frames with Hand Detection: {data['frames_with_detection']} ({data['frames_with_detection']/data['total_frames']*100:.1f}%)")
        print(f"\n  Expected Hand IN Zone: {data['hand_in_zone_expected']} frames")
        print(f"  Correctly Detected IN Zone: {data['true_positives']} ({data['true_positives']/data['hand_in_zone_expected']*100:.1f}%)")
        print(f"  Missed IN Zone: {data['false_negatives']} ({data['false_negatives']/data['hand_in_zone_expected']*100:.1f}%)")
        print(f"\n  Expected Hand OUT of Zone: {data['hand_out_zone_expected']} frames")
        print(f"  Correctly Detected OUT of Zone: {data['true_negatives']} ({data['true_negatives']/data['hand_out_zone_expected']*100:.1f}%)")
        print(f"  Falsely Detected IN Zone: {data['false_positives']} ({data['false_positives']/data['hand_out_zone_expected']*100:.1f}%)")
        print(f"\n  Overall Accuracy: {(data['true_positives'] + data['true_negatives'])/data['total_frames']*100:.1f}%")
    
    print("\n" + "="*100)
    print("\nNOTES:")
    print("- 'Detection' = percentage of frames where any hand was detected")
    print("- 'Accuracy' = percentage of frames where zone detection matched expected state")
    print("- 'True Pos' = correctly detected hand in zone when expected")
    print("- 'False Neg' = failed to detect hand in zone when expected")
    print("- 'False Pos' = incorrectly detected hand in zone when not expected")
    print("- Each cycle = hand moved IN then OUT of zone")
    print("="*100 + "\n")

def main():
    """Main function to run the lighting conditions experiment"""
    print("="*80)
    print("LIGHTING CONDITIONS EXPERIMENT")
    print("="*80)
    print("\nThis experiment will test hand detection under different lighting:")
    print("  - LOW: Dim lighting (e.g., single lamp, curtains closed)")
    print("  - AMBIENT: Normal room lighting")
    print("  - HIGH: Bright lighting (e.g., overhead lights, window open)")
    print("\nFor each condition, move your hand IN and OUT of the target zone.")
    print("Complete 20 cycles (20 times in, 20 times out).")
    print("Stand 5 feet from the camera.")
    print("\nPress SPACE to toggle between IN/OUT states as you move your hand.")
    print("\nPress ENTER to start or 'q' to quit...")
    
    user_input = input()
    if user_input.lower() == 'q':
        return
    
    lighting_conditions = ['low', 'ambient', 'high']
    all_data = []
    
    for condition in lighting_conditions:
        print(f"\n\n{'='*80}")
        print(f"PREPARE FOR {condition.upper()} LIGHTING TEST")
        print(f"{'='*80}")
        print(f"\nAdjust your lighting to {condition.upper()} conditions:")
        
        if condition == 'low':
            print("  - Turn off overhead lights")
            print("  - Close curtains/blinds")
            print("  - Use only minimal ambient light")
        elif condition == 'ambient':
            print("  - Use normal room lighting")
            print("  - Typical indoor conditions")
        elif condition == 'high':
            print("  - Turn on all overhead lights")
            print("  - Open curtains/blinds")
            print("  - Maximize available light")
        
        print("\nPosition yourself 5 feet from the camera.")
        print("Start with your hand OUT of the zone.")
        print("\nPress ENTER when ready (or 'q' to skip)...")
        
        user_input = input()
        if user_input.lower() == 'q':
            continue
        
        data = collect_lighting_data(condition, target_cycles=20)
        if data is not None:
            all_data.append(data)
        
        print(f"\nCompleted {condition} lighting test!")
    
    if all_data:
        print_summary(all_data)
        
        # Save results to file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"lighting_test_results_{timestamp}.txt"
        
        with open(filename, 'w') as f:
            f.write("LIGHTING CONDITIONS TEST RESULTS\n")
            f.write("="*80 + "\n\n")
            f.write(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            for data in all_data:
                f.write(f"\n{data['lighting_condition'].upper()} LIGHTING:\n")
                f.write(f"  Cycles Completed: {data['cycles_completed']}\n")
                f.write(f"  Total Frames: {data['total_frames']}\n")
                f.write(f"  Average Brightness: {np.mean(data['brightness_samples']):.1f}\n")
                f.write(f"  Frames with Detection: {data['frames_with_detection']}\n")
                f.write(f"  Hand In Zone (Expected): {data['hand_in_zone_expected']}\n")
                f.write(f"  Hand In Zone (Detected): {data['hand_in_zone_detected']}\n")
                f.write(f"  True Positives: {data['true_positives']}\n")
                f.write(f"  False Negatives: {data['false_negatives']}\n")
                f.write(f"  True Negatives: {data['true_negatives']}\n")
                f.write(f"  False Positives: {data['false_positives']}\n")
                accuracy = (data['true_positives'] + data['true_negatives'])/data['total_frames']*100
                f.write(f"  Accuracy: {accuracy:.1f}%\n")
        
        print(f"\nResults saved to: {filename}")
    
    print("\nLighting conditions experiment complete!")

if __name__ == "__main__":
    main()

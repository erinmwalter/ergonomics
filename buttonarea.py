import cv2
import numpy as np
from ultralytics import YOLO

# Load pose model
pose_model = YOLO('yolo11n-pose.pt')

# DEFINE YOUR BUTTON AREA HERE - Change these coordinates to match where you want the button
BUTTON_TOP_LEFT = (300, 200)      # (x, y) top-left corner
BUTTON_BOTTOM_RIGHT = (500, 350)  # (x, y) bottom-right corner
button_interactions = {}

def get_hand_positions(keypoints, conf_threshold=0.7):
    """Extract left and right hand positions from pose keypoints with better accuracy"""
    hands = {'left': None, 'right': None}
    
    for person_kp in keypoints:
        if len(person_kp) > 10:
            left_wrist = person_kp[9]   # Left wrist
            right_wrist = person_kp[10] # Right wrist
            
            # Higher confidence threshold to reduce hallucinations
            if left_wrist[2] > conf_threshold:
                # Add offset to get actual hand position (hand is below wrist)
                hand_x = int(left_wrist[0])
                hand_y = int(left_wrist[1] + 30)  # Offset down by 30 pixels
                
                # Sanity check - make sure coordinates are reasonable
                if 0 <= hand_x <= 1920 and 0 <= hand_y <= 1080:  # Typical screen bounds
                    hands['left'] = (hand_x, hand_y)
            
            if right_wrist[2] > conf_threshold:
                # Add offset to get actual hand position
                hand_x = int(right_wrist[0])
                hand_y = int(right_wrist[1] + 30)  # Offset down by 30 pixels
                
                # Sanity check
                if 0 <= hand_x <= 1920 and 0 <= hand_y <= 1080:
                    hands['right'] = (hand_x, hand_y)
    
    return hands

def is_hand_in_button_area(hand_pos):
    """Check if hand is inside the button rectangle"""
    if hand_pos is None:
        return False
    
    hand_x, hand_y = hand_pos
    x1, y1 = BUTTON_TOP_LEFT
    x2, y2 = BUTTON_BOTTOM_RIGHT
    
    # Check if hand is within the rectangle
    return x1 <= hand_x <= x2 and y1 <= hand_y <= y2

def draw_button_area(img):
    """Draw the button area as a rectangle"""
    x1, y1 = BUTTON_TOP_LEFT
    x2, y2 = BUTTON_BOTTOM_RIGHT
    
    # Draw the button rectangle outline
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 3)  # Yellow rectangle
    
    # Draw corner markers for visibility
    corner_size = 10
    # Top-left corner
    cv2.line(img, (x1, y1), (x1 + corner_size, y1), (0, 255, 255), 5)
    cv2.line(img, (x1, y1), (x1, y1 + corner_size), (0, 255, 255), 5)
    
    # Top-right corner
    cv2.line(img, (x2, y1), (x2 - corner_size, y1), (0, 255, 255), 5)
    cv2.line(img, (x2, y1), (x2, y1 + corner_size), (0, 255, 255), 5)
    
    # Bottom-left corner
    cv2.line(img, (x1, y2), (x1 + corner_size, y2), (0, 255, 255), 5)
    cv2.line(img, (x1, y2), (x1, y2 - corner_size), (0, 255, 255), 5)
    
    # Bottom-right corner
    cv2.line(img, (x2, y2), (x2 - corner_size, y2), (0, 255, 255), 5)
    cv2.line(img, (x2, y2), (x2, y2 - corner_size), (0, 255, 255), 5)
    
    # Add center point
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    cv2.circle(img, (center_x, center_y), 5, (0, 255, 255), -1)
    
    # Label the button
    label_x = x1
    label_y = y1 - 10 if y1 - 10 > 0 else y1 + 20
    cv2.putText(img, "BUTTON AREA", (label_x, label_y), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
    
    return img

def draw_hand_boxes(img, hands, box_size=60):
    """Draw bounding boxes around detected hands with confidence indicators"""
    colors = {'left': (0, 255, 0), 'right': (255, 0, 0)}
    
    for hand_type, position in hands.items():
        if position is not None:
            x, y = position
            color = colors[hand_type]
            
            # Draw bounding box
            half_size = box_size // 2
            cv2.rectangle(img, (x - half_size, y - half_size), 
                         (x + half_size, y + half_size), color, 2)
            
            # Add label with "HAND" to be more specific
            cv2.putText(img, f"{hand_type.upper()} HAND", (x - half_size, y - half_size - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Draw center point (this is the actual tracking point)
            cv2.circle(img, (x, y), 6, color, -1)
            
            # Draw wrist reference point (30 pixels up)
            wrist_y = y - 30
            cv2.circle(img, (x, wrist_y), 3, (128, 128, 128), -1)
            cv2.line(img, (x, y), (x, wrist_y), (128, 128, 128), 1)
    
    return img

def check_button_interactions(hands, frame_count):
    """Check for hand-button interactions and log them"""
    global button_interactions
    
    # Check each hand
    for hand_type, hand_pos in hands.items():
        if is_hand_in_button_area(hand_pos):
            # Check if this is a new interaction
            if hand_type not in button_interactions:
                button_interactions[hand_type] = frame_count
                print(f"🔴 BUTTON PRESSED! {hand_type.upper()} hand entered button area at frame {frame_count}")
        else:
            # Remove interaction if hand moved away
            if hand_type in button_interactions:
                duration = frame_count - button_interactions[hand_type]
                print(f"🔵 Button released by {hand_type.upper()} hand (in area for {duration} frames)")
                del button_interactions[hand_type]

def main():
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    print("Rectangular Button Area Tracker Started!")
    print("📋 Instructions:")
    print(f"1. Button area is from {BUTTON_TOP_LEFT} to {BUTTON_BOTTOM_RIGHT}")
    print("2. Position your paper button inside the yellow rectangle")
    print("3. To change button area, modify BUTTON_TOP_LEFT and BUTTON_BOTTOM_RIGHT in code")
    print("4. Move your hands into the yellow rectangle to 'press' the button")
    print("5. Watch console for button press events!")
    print("6. Press 'q' to quit")
    
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        frame_count += 1
        
        # Run pose detection
        pose_results = pose_model(frame, verbose=False)
        
        hands = {'left': None, 'right': None}
        
        # Process pose results with additional validation
        for result in pose_results:
            if result.keypoints is not None and len(result.keypoints.xy) > 0:
                keypoints = result.keypoints.xy.cpu().numpy()
                confidences = result.keypoints.conf.cpu().numpy()
                
                # Only process if we actually detected a person
                if len(keypoints) > 0 and len(keypoints[0]) > 10:
                    kp_data = []
                    for i in range(len(keypoints)):
                        person_kp = []
                        for j in range(len(keypoints[i])):
                            x, y = keypoints[i][j]
                            conf = confidences[i][j]
                            person_kp.append([x, y, conf])
                        kp_data.append(person_kp)
                    
                    hands = get_hand_positions(kp_data)
        
        # Check for interactions
        if hands['left'] or hands['right']:
            check_button_interactions(hands, frame_count)
        
        # Draw everything
        frame = draw_button_area(frame)
        frame = draw_hand_boxes(frame, hands)
        
        # Status display
        cv2.putText(frame, f"Button: {BUTTON_TOP_LEFT} to {BUTTON_BOTTOM_RIGHT}", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Show active interactions
        y_offset = 60
        for hand_type in button_interactions:
            cv2.putText(frame, f"{hand_type.upper()} IN BUTTON AREA", 
                       (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
            y_offset += 25
        
        # Show hand positions for debugging with confidence info
        detected_hands = sum(1 for pos in hands.values() if pos is not None)
        cv2.putText(frame, f"Hands detected: {detected_hands}/2", 
                   (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        y_offset += 25
        
        for hand_type, position in hands.items():
            if position is not None:
                in_area = "IN AREA" if is_hand_in_button_area(position) else "outside"
                cv2.putText(frame, f"{hand_type}: {position} ({in_area})", 
                           (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                y_offset += 20
        
        cv2.imshow('Rectangular Button SOP Monitor', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    print("Tracker stopped.")

if __name__ == "__main__":
    main()
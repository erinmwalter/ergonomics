import cv2
import numpy as np
from ultralytics import YOLO

model = YOLO('yolo11n-pose.pt')

def get_hand_positions(keypoints, conf_threshold=0.5):
    hands = {'left': None, 'right': None}
    
    for person_kp in keypoints:
        if len(person_kp) > 10:  # Ensure we have enough keypoints
            left_wrist = person_kp[9]   # Left wrist (COCO format)
            right_wrist = person_kp[10] # Right wrist (COCO format)
            
            if left_wrist[2] > conf_threshold:  # Check confidence
                hands['left'] = (int(left_wrist[0]), int(left_wrist[1]))
            if right_wrist[2] > conf_threshold:
                hands['right'] = (int(right_wrist[0]), int(right_wrist[1]))
    
    return hands

def draw_hand_boxes(img, hands, box_size=60):
    """Draw bounding boxes around detected hands"""
    colors = {'left': (0, 255, 0), 'right': (255, 0, 0)}  # Green for left, Red for right
    
    for hand_type, position in hands.items():
        if position is not None:
            x, y = position
            color = colors[hand_type]
            
            # Draw bounding box
            half_size = box_size // 2
            top_left = (x - half_size, y - half_size)
            bottom_right = (x + half_size, y + half_size)
            
            cv2.rectangle(img, top_left, bottom_right, color, 2)
            
            # Add label
            label = f"{hand_type.upper()} HAND"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
            label_y = y - half_size - 10 if y - half_size - 10 > 0 else y + half_size + 20
            
            cv2.rectangle(img, 
                         (x - half_size, label_y - label_size[1] - 5),
                         (x - half_size + label_size[0] + 10, label_y + 5),
                         color, -1)
            
            cv2.putText(img, label, (x - half_size + 5, label_y), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            
            # Draw center point
            cv2.circle(img, (x, y), 4, color, -1)
    
    return img

def main():
    # Open webcam
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    print("Hand Tracker Started!")
    print("Press 'q' to quit")
    print("Green box = Left Hand, Red box = Right Hand")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read frame")
            break
        
        # Run YOLO pose detection
        results = model(frame, verbose=False)
        
        # Process results
        for result in results:
            if result.keypoints is not None:
                # Extract keypoints and confidences
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
                
                # Draw hand boxes
                frame = draw_hand_boxes(frame, hands)
                
                # Display hand coordinates in corner
                y_offset = 30
                for hand_type, position in hands.items():
                    if position is not None:
                        text = f"{hand_type.upper()}: ({position[0]}, {position[1]})"
                        cv2.putText(frame, text, (10, y_offset), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                        y_offset += 30
        
        # Display the frame
        cv2.imshow('Hand Tracker - SOP Monitoring', frame)
        
        # Check for quit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    print("Hand Tracker stopped.")

if __name__ == "__main__":
    main()
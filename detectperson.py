import cv2
from ultralytics import YOLO

# Load YOLOv11 pose model
model = YOLO('yolo11n-pose.pt')  # Use yolo11s-pose.pt, yolo11m-pose.pt for better accuracy

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

def draw_hand_boxes(img, keypoints, conf_threshold=0.5, box_size=40):
    """Draw bounding boxes around left & right hands."""
    for kp in keypoints:
        # Left wrist = index 9
        # Right wrist = index 10
        for idx, color in [(9, (0, 255, 0)), (10, (0, 0, 255))]:
            if idx < len(kp):
                x, y, conf = kp[idx]
                
                if conf > conf_threshold:
                    x, y = int(x), int(y)

                    # Draw box around hand
                    cv2.rectangle(
                        img,
                        (x - box_size, y - box_size),
                        (x + box_size, y + box_size),
                        color,
                        2
                    )

                    # Optional: Draw center dot
                    cv2.circle(img, (x, y), 4, color, -1)

    return img

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

# Open video capture (0 for webcam, or provide video path)
cap = cv2.VideoCapture(0)

# Or use a video file:
# cap = cv2.VideoCapture('path/to/video.mp4')

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    # Run YOLOv11 pose detection
    results = model(frame, verbose=False)
    
    # Draw poses on frame
    for result in results:
        if result.keypoints is not None:
            keypoints = result.keypoints.xy.cpu().numpy()  # Get keypoint coordinates
            confidences = result.keypoints.conf.cpu().numpy()  # Get confidences
            
            # Combine coordinates with confidences
            kp_data = []
            for i in range(len(keypoints)):
                person_kp = []
                for j in range(len(keypoints[i])):
                    x, y = keypoints[i][j]
                    conf = confidences[i][j]
                    person_kp.append([x, y, conf])
                kp_data.append(person_kp)
            
           #frame = draw_pose(frame, kp_data)
            frame = draw_hand_boxes(frame, kp_data)
    
    # Display the frame
    cv2.imshow('YOLOv11 Pose Detection', frame)
    
    # Press 'q' to quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
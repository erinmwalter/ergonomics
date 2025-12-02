import cv2
import time
from ultralytics import YOLO

model = YOLO('yolo11n-pose.pt')

LEFT_WRIST_IDX = 9
RIGHT_WRIST_IDX = 10

zones = [
    {'id': 1, 'name': 'Zone A', 'x': 100, 'y': 100, 'width': 150, 'height': 150, 'color': (0, 255, 0)},
    {'id': 2, 'name': 'Zone B', 'x': 300, 'y': 100, 'width': 150, 'height': 150, 'color': (255, 0, 0)},
    {'id': 3, 'name': 'Zone C', 'x': 200, 'y': 300, 'width': 150, 'height': 150, 'color': (0, 0, 255)},
]

process_sequence = [1, 2, 3]

current_step = 0
process_complete = False
step_times = []
process_start_time = None
in_zone = False
entry_time = None

def check_hand_in_zone(x, y, zone):
    return (zone['x'] <= x <= zone['x'] + zone['width'] and 
            zone['y'] <= y <= zone['y'] + zone['height'])

def draw_zones(frame):
    for i, zone in enumerate(zones):
        color = zone['color']
        thickness = 2
        
        if i == current_step and not process_complete:
            color = (0, 255, 255)
            thickness = 3
        elif i < current_step:
            color = (0, 200, 0)
        
        cv2.rectangle(frame, 
                     (zone['x'], zone['y']), 
                     (zone['x'] + zone['width'], zone['y'] + zone['height']),
                     color, thickness)
        
        cv2.putText(frame, zone['name'], 
                   (zone['x'], zone['y'] - 10),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

cap = cv2.VideoCapture(0)

print("Process Sequence Tracker Started")
print(f"Required sequence: {[zones[i-1]['name'] for i in process_sequence]}")
print("Press 'q' to quit\n")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    results = model(frame, verbose=False)
    
    draw_zones(frame)
    
    if not process_complete and current_step < len(process_sequence):
        target_zone_id = process_sequence[current_step]
        target_zone = zones[target_zone_id - 1]
        
        hand_detected = False
        hand_type = None
        
        for result in results:
            if result.keypoints is not None:
                keypoints = result.keypoints.xy.cpu().numpy()
                confidences = result.keypoints.conf.cpu().numpy()
                
                for person_kp, person_conf in zip(keypoints, confidences):
                    if LEFT_WRIST_IDX < len(person_kp) and person_conf[LEFT_WRIST_IDX] > 0.5:
                        x, y = person_kp[LEFT_WRIST_IDX]
                        if check_hand_in_zone(x, y, target_zone):
                            hand_detected = True
                            hand_type = "left"
                            break
                    
                    if RIGHT_WRIST_IDX < len(person_kp) and person_conf[RIGHT_WRIST_IDX] > 0.5:
                        x, y = person_kp[RIGHT_WRIST_IDX]
                        if check_hand_in_zone(x, y, target_zone):
                            hand_detected = True
                            hand_type = "right"
                            break
        
        if hand_detected and not in_zone:
            in_zone = True
            entry_time = time.time()
            
            if process_start_time is None:
                process_start_time = time.time()
            
            step_time = entry_time - (step_times[-1] if step_times else process_start_time)
            step_times.append(step_time)
            
            print(f"✓ Step {current_step + 1}/{len(process_sequence)} completed: {target_zone['name']} ({hand_type} hand) - Time: {step_time:.2f}s")
            
            current_step += 1
            
            if current_step >= len(process_sequence):
                process_complete = True
                total_time = time.time() - process_start_time
                print(f"\nPROCESS COMPLETE!")
                print(f"Total time: {total_time:.2f}s")
                print(f"Step times: {[f'{t:.2f}s' for t in step_times]}")
        
        elif not hand_detected and in_zone:
            in_zone = False
    
    status_text = f"Step: {current_step}/{len(process_sequence)}"
    if process_complete:
        status_text = "COMPLETE!"
    elif current_step < len(process_sequence):
        status_text += f" - Next: {zones[process_sequence[current_step]-1]['name']}"
    
    cv2.putText(frame, status_text, (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow('Sequential Process Tracker', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
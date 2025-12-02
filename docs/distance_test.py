import cv2
import time
import csv
from datetime import datetime
from ultralytics import YOLO

model = YOLO('yolo11n-pose.pt')

LEFT_WRIST_IDX = 9
RIGHT_WRIST_IDX = 10

test_zone = {
    'name': 'Test Zone',
    'x': 250,
    'y': 150,
    'width': 200,
    'height': 200
}

test_distance = input("Enter test distance (3ft/6ft/9ft/12ft): ")
trial_number = 0
max_trials = 20

data_log = []
in_zone = False
detection_count = 0
frame_count = 0

def check_hand_in_zone(x, y, zone):
    return (zone['x'] <= x <= zone['x'] + zone['width'] and 
            zone['y'] <= y <= zone['y'] + zone['height'])

def draw_zone(frame, zone, highlight=False):
    color = (0, 0, 255) if highlight else (0, 255, 0)
    thickness = 3 if highlight else 2
    cv2.rectangle(frame, 
                 (zone['x'], zone['y']), 
                 (zone['x'] + zone['width'], zone['y'] + zone['height']),
                 color, thickness)
    cv2.putText(frame, zone['name'], 
               (zone['x'], zone['y'] - 10),
               cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print(f"\nDistance Test: {test_distance.upper()}")
print(f"Target: {max_trials} zone entries")
print("Move your hand in and out of the zone")
print("Press 'q' to finish early\n")

start_time = time.time()

while cap.isOpened() and trial_number < max_trials:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame_count += 1
    results = model(frame, verbose=False)
    
    hand_detected = False
    hand_position = None
    confidence_score = 0
    hand_type = None
    
    for result in results:
        if result.keypoints is not None:
            keypoints = result.keypoints.xy.cpu().numpy()
            confidences = result.keypoints.conf.cpu().numpy()
            
            for person_kp, person_conf in zip(keypoints, confidences):
                if LEFT_WRIST_IDX < len(person_kp) and person_conf[LEFT_WRIST_IDX] > 0.5:
                    x, y = person_kp[LEFT_WRIST_IDX]
                    conf = person_conf[LEFT_WRIST_IDX]
                    if check_hand_in_zone(x, y, test_zone):
                        hand_detected = True
                        hand_position = (int(x), int(y))
                        confidence_score = float(conf)
                        hand_type = "left"
                        break
                
                if not hand_detected and RIGHT_WRIST_IDX < len(person_kp) and person_conf[RIGHT_WRIST_IDX] > 0.5:
                    x, y = person_kp[RIGHT_WRIST_IDX]
                    conf = person_conf[RIGHT_WRIST_IDX]
                    if check_hand_in_zone(x, y, test_zone):
                        hand_detected = True
                        hand_position = (int(x), int(y))
                        confidence_score = float(conf)
                        hand_type = "right"
                        break
    
    if hand_detected and not in_zone:
        in_zone = True
        trial_number += 1
        detection_count += 1
        
        log_entry = {
            'distance': test_distance,
            'trial': trial_number,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],
            'hand_type': hand_type,
            'confidence': round(confidence_score, 3),
            'x_position': hand_position[0],
            'y_position': hand_position[1],
            'frame_number': frame_count
        }
        data_log.append(log_entry)
        
        print(f"Trial {trial_number}/{max_trials} - {hand_type} hand - Confidence: {confidence_score:.3f}")
    
    elif not hand_detected and in_zone:
        in_zone = False
    
    draw_zone(frame, test_zone, hand_detected)
    
    if hand_detected and hand_position:
        cv2.circle(frame, hand_position, 8, (0, 255, 255), -1)
    
    status_text = f"Distance: {test_distance.upper()} | Trial: {trial_number}/{max_trials}"
    cv2.putText(frame, status_text, (10, 30), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow('Distance Test', frame)
    
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()

total_time = time.time() - start_time

csv_filename = f'distance_test_{test_distance}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
with open(csv_filename, 'w', newline='') as csvfile:
    if data_log:
        fieldnames = data_log[0].keys()
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data_log)

print(f"\n{'='*50}")
print(f"Distance Test Complete: {test_distance.upper()}")
print(f"{'='*50}")
print(f"Total detections: {detection_count}/{max_trials} ({detection_count/max_trials*100:.1f}%)")
print(f"Total time: {total_time:.1f}s")
print(f"Average time per trial: {total_time/trial_number:.1f}s")

if data_log:
    avg_confidence = sum(d['confidence'] for d in data_log) / len(data_log)
    print(f"Average confidence: {avg_confidence:.3f}")
    print(f"\nData saved to: {csv_filename}")
else:
    print("No data collected")
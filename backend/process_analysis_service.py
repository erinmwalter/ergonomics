import cv2
import numpy as np
from ultralytics import YOLO
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from database import DatabaseService

class ProcessAnalysisService:
    def __init__(self):
        self.model = YOLO('yolo11n-pose.pt')
        
        self.db = DatabaseService(database="postgres")
        
        self.is_tracking = False
        self.current_process = None
        self.current_zones = []
        self.process_steps = []
        self.session_data = {
            'start_time': None,
            'step_events': [],
            'current_step': 0,
            'zone_hits': [],
            'completion_times': []
        }
        
        self.conf_threshold = 0.5
        self.hand_offset_pixels = 30
        
    def load_process(self, environment_id: int, process_id: int):
        """Load process and zones for tracking"""
        try:
            self.current_process = self.db.get_process_by_id(process_id)
            if not self.current_process:
                raise ValueError(f"Process {process_id} not found")
            
            self.current_zones = self.db.get_zones_for_environment(environment_id)
            
            self.process_steps = self.db.get_process_steps(process_id)
            
            print(f"Loaded process: {self.current_process['ProcessName']}")
            print(f"Zones: {len(self.current_zones)}")
            print(f"Steps: {len(self.process_steps)}")
            
            return True
            
        except Exception as e:
            print(f"Error loading process: {e}")
            return False
    
    def start_tracking(self):
        """Start process tracking session"""
        if not self.current_process or not self.process_steps:
            raise ValueError("No process loaded. Call load_process() first.")
            
        self.is_tracking = True
        self.session_data = {
            'start_time': time.time(),
            'step_events': [],
            'current_step': 0,
            'zone_hits': [],
            'completion_times': [],
            'process_id': self.current_process['Id']
        }
        
        print(f"Started tracking process: {self.current_process['ProcessName']}")
        print(f"Expected sequence: {[step['StepName'] for step in self.process_steps]}")
    
    def stop_tracking(self):
        """Stop tracking and return results"""
        if not self.is_tracking:
            return None
            
        self.is_tracking = False
        end_time = time.time()
        total_time = end_time - self.session_data['start_time']
        
        results = self.calculate_adherence_metrics(total_time)
        
        # TODO: Save session to database
        # self.save_session_to_db(results)
        
        print(f"Tracking stopped. Total time: {total_time:.2f}s")
        return results
    
    def get_hand_positions(self, keypoints, confidences):
        """Extract hand positions from pose keypoints"""
        hands = {'left': None, 'right': None}
        
        # YOLO pose keypoint indices
        LEFT_WRIST = 9   # Left wrist
        RIGHT_WRIST = 10 # Right wrist
        
        for person_idx in range(len(keypoints)):
            person_kp = keypoints[person_idx]
            person_conf = confidences[person_idx]
            
            # Left hand (from left wrist + offset)
            if LEFT_WRIST < len(person_kp) and person_conf[LEFT_WRIST] > self.conf_threshold:
                wrist_x, wrist_y = person_kp[LEFT_WRIST]
                # Add offset to approximate hand position
                hand_x = wrist_x + self.hand_offset_pixels
                hand_y = wrist_y + self.hand_offset_pixels
                hands['left'] = (int(hand_x), int(hand_y))
            
            # Right hand (from right wrist + offset) 
            if RIGHT_WRIST < len(person_kp) and person_conf[RIGHT_WRIST] > self.conf_threshold:
                wrist_x, wrist_y = person_kp[RIGHT_WRIST]
                # Add offset to approximate hand position
                hand_x = wrist_x - self.hand_offset_pixels  # Negative for right hand
                hand_y = wrist_y + self.hand_offset_pixels
                hands['right'] = (int(hand_x), int(hand_y))
        
        return hands
    
    def check_zone_collision(self, hand_pos: Tuple[int, int], zone: Dict) -> bool:
        """Check if hand position is inside a zone"""
        if not hand_pos:
            return False
            
        x, y = hand_pos
        return (zone['Xstart'] <= x <= zone['Xend'] and 
                zone['Ystart'] <= y <= zone['Yend'])
    
    def process_frame(self, frame):
        """Process a single frame for pose detection and zone tracking"""
        if not self.is_tracking:
            return frame
            
        # Run YOLO pose detection
        results = self.model(frame, verbose=False)
        
        # Draw zones on frame
        frame = self.draw_zones(frame)
        
        # Process pose detection results
        for result in results:
            if result.keypoints is not None:
                keypoints = result.keypoints.xy.cpu().numpy()
                confidences = result.keypoints.conf.cpu().numpy()
                
                # Get hand positions
                hands = self.get_hand_positions(keypoints, confidences)
                
                # Draw hands
                frame = self.draw_hands(frame, hands)
                
                # Check zone collisions and process steps
                self.check_step_progress(hands)
        
        # Draw process status
        frame = self.draw_process_status(frame)
        
        return frame
    
    def draw_zones(self, frame):
        """Draw zones on the frame"""
        for zone in self.current_zones:
            # Zone rectangle
            start_point = (zone['Xstart'], zone['Ystart'])
            end_point = (zone['Xend'], zone['Yend'])
            
            # Convert hex color to BGR
            color_hex = zone['Color'].lstrip('#')
            color_bgr = tuple(int(color_hex[i:i+2], 16) for i in (4, 2, 0))  # BGR format
            
            cv2.rectangle(frame, start_point, end_point, color_bgr, 2)
            
            # Zone label
            cv2.putText(frame, zone['ZoneName'], 
                       (zone['Xstart'], zone['Ystart'] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color_bgr, 2)
        
        return frame
    
    def draw_hands(self, frame, hands):
        """Draw hand positions on frame"""
        for hand_type, pos in hands.items():
            if pos:
                color = (0, 255, 0) if hand_type == 'left' else (0, 0, 255)  # Green for left, red for right
                cv2.circle(frame, pos, 8, color, -1)
                cv2.putText(frame, f"{hand_type.upper()}", 
                           (pos[0] - 20, pos[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        return frame
    
    def draw_process_status(self, frame):
        """Draw current process status on frame"""
        if not self.process_steps:
            return frame
            
        current_step_idx = self.session_data['current_step']
        
        # Status background
        overlay = frame.copy()
        cv2.rectangle(overlay, (10, 10), (400, 120), (0, 0, 0), -1)
        frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
        
        # Process name
        cv2.putText(frame, f"Process: {self.current_process['ProcessName']}", 
                   (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Current step
        if current_step_idx < len(self.process_steps):
            current_step = self.process_steps[current_step_idx]
            cv2.putText(frame, f"Step {current_step_idx + 1}: {current_step['StepName']}", 
                       (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.putText(frame, f"Target: {current_step['ZoneName']} ({current_step['Duration']}s)", 
                       (20, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        else:
            cv2.putText(frame, "Process Complete!", 
                       (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Progress
        progress = f"Progress: {current_step_idx}/{len(self.process_steps)}"
        cv2.putText(frame, progress, (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return frame
    
    def check_step_progress(self, hands):
        """Check if current step is completed based on hand positions"""
        if not self.is_tracking or not self.process_steps:
            return
            
        current_step_idx = self.session_data['current_step']
        if current_step_idx >= len(self.process_steps):
            return  # Process already complete
            
        current_step = self.process_steps[current_step_idx]
        target_zone_id = current_step['TargetZoneId']
        
        # Find the target zone
        target_zone = None
        for zone in self.current_zones:
            if zone['Id'] == target_zone_id:
                target_zone = zone
                break
        
        if not target_zone:
            return
            
        # Check if either hand is in the target zone
        hit_detected = False
        for hand_type, hand_pos in hands.items():
            if hand_pos and self.check_zone_collision(hand_pos, target_zone):
                hit_detected = True
                break
        
        # Record the hit and advance step if needed
        if hit_detected:
            current_time = time.time()
            step_time = current_time - (self.session_data['step_events'][-1]['time'] if self.session_data['step_events'] else self.session_data['start_time'])
            
            # Record step completion
            step_event = {
                'step_number': current_step_idx + 1,
                'step_name': current_step['StepName'],
                'zone_hit': target_zone['ZoneName'],
                'time': current_time,
                'duration': step_time,
                'target_duration': current_step['Duration']
            }
            
            self.session_data['step_events'].append(step_event)
            self.session_data['current_step'] += 1
            
            print(f"Step {current_step_idx + 1} completed in {step_time:.2f}s (target: {current_step['Duration']}s)")
    
    def calculate_adherence_metrics(self, total_time):
        """Calculate process adherence metrics"""
        if not self.session_data['step_events']:
            return {'adherence_score': 0, 'message': 'No steps completed'}
        
        total_steps = len(self.process_steps)
        completed_steps = len(self.session_data['step_events'])
        
        # Step completion adherence
        completion_adherence = (completed_steps / total_steps) * 100
        
        # Timing adherence
        timing_scores = []
        for event in self.session_data['step_events']:
            target_time = event['target_duration']
            actual_time = event['duration']
            
            # Score based on how close to target time (100% if within 20% of target)
            time_ratio = actual_time / target_time
            if time_ratio <= 1.2:  # Within 20% of target
                timing_score = 100
            elif time_ratio <= 2.0:  # Within 100% of target
                timing_score = max(0, 100 - (time_ratio - 1) * 100)
            else:
                timing_score = 0
            
            timing_scores.append(timing_score)
        
        avg_timing_adherence = sum(timing_scores) / len(timing_scores) if timing_scores else 0
        
        # Overall adherence (weighted average)
        overall_adherence = (completion_adherence * 0.7) + (avg_timing_adherence * 0.3)
        
        return {
            'overall_adherence': round(overall_adherence, 2),
            'completion_adherence': round(completion_adherence, 2),
            'timing_adherence': round(avg_timing_adherence, 2),
            'completed_steps': completed_steps,
            'total_steps': total_steps,
            'total_time': round(total_time, 2),
            'target_total_time': sum(step['Duration'] for step in self.process_steps),
            'step_details': self.session_data['step_events']
        }

# Example usage / testing
if __name__ == "__main__":
    service = ProcessAnalysisService()
    
    # Test loading a process (you'll need to have data in your database)
    if service.load_process(environment_id=1, process_id=1):
        cap = cv2.VideoCapture(0)
        
        print("Press 's' to start tracking, 'q' to quit, 'x' to stop tracking")
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Process frame
            frame = service.process_frame(frame)
            
            # Display frame
            cv2.imshow('Process Analysis', frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s') and not service.is_tracking:
                service.start_tracking()
            elif key == ord('x') and service.is_tracking:
                results = service.stop_tracking()
                if results:
                    print("\nProcess Analysis Results:")
                    print(f"Overall Adherence: {results['overall_adherence']}%")
                    print(f"Completion: {results['completed_steps']}/{results['total_steps']} steps")
                    print(f"Time: {results['total_time']}s (target: {results['target_total_time']}s)")
        
        cap.release()
        cv2.destroyAllWindows()
    else:
        print("Failed to load process. Make sure you have data in your database.")
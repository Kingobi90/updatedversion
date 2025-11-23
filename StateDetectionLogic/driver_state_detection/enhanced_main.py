"""
Enhanced Study Focus Detection System
Integrates object detection, context analysis, adaptive thresholds, and pattern recognition
"""

import os
import socket
import time
import pprint
import requests
import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

try:
    from .attention_scorer import AttentionScorer as AttScorer
    from .eye_detector import EyeDetector as EyeDet
    from .parser import get_args
    from .pose_estimation import HeadPoseEstimator as HeadPoseEst
    from .utils import get_landmarks, load_camera_parameters
    from .object_detector import ObjectDetector
    from .context_analyzer import ContextAnalyzer, ActivityType
    from .adaptive_scorer import AdaptiveAttentionScorer
    from .pattern_recognizer import PatternRecognizer
    from .server_reporter import ServerReporter
except ImportError:
    from attention_scorer import AttentionScorer as AttScorer
    from eye_detector import EyeDetector as EyeDet
    from parser import get_args
    from pose_estimation import HeadPoseEstimator as HeadPoseEst
    from utils import get_landmarks, load_camera_parameters
    from object_detector import ObjectDetector
    from context_analyzer import ContextAnalyzer, ActivityType
    from adaptive_scorer import AdaptiveAttentionScorer
    from pattern_recognizer import PatternRecognizer
    from server_reporter import ServerReporter


def get_local_ip():
    """Auto-detect local IP address."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def main():
    # Load environment variables
    env_path = Path(__file__).parent.parent / '.env'
    load_dotenv(dotenv_path=env_path)
    
    # Get server URL from environment or auto-detect
    SERVER_URL = os.getenv('SERVER_URL', '').strip()
    if not SERVER_URL:
        # Auto-detect: use local IP with default port
        local_ip = get_local_ip()
        port = os.getenv('PORT', '3000')
        SERVER_URL = f"http://{local_ip}:{port}"
        print(f"Auto-detected SERVER_URL: {SERVER_URL}")
    
    args = get_args()
    
    # OpenCV optimization
    if not cv2.useOptimized():
        try:
            cv2.setUseOptimized(True)
        except Exception as e:
            print(f"OpenCV optimization could not be set: {e}")
    
    # Load camera parameters
    if args.camera_params:
        camera_matrix, dist_coeffs = load_camera_parameters(args.camera_params)
    else:
        camera_matrix, dist_coeffs = None, None
    
    if args.verbose:
        print("Enhanced Study Focus Detection System")
        print("=" * 50)
        print("\nArguments:")
        pprint.pp(vars(args), indent=4)
        print("\nCamera Matrix:")
        pprint.pp(camera_matrix, indent=4)
        print("\n")
    
    # Initialize MediaPipe Face Mesh
    Detector = mp.solutions.face_mesh.FaceMesh(
        static_image_mode=False,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        refine_landmarks=True,
    )
    
    # Initialize detectors
    Eye_det = EyeDet(show_processing=args.show_eye_proc)
    Head_pose = HeadPoseEst(
        show_axis=args.show_axis,
        camera_matrix=camera_matrix,
        dist_coeffs=dist_coeffs
    )
    
    # Initialize NEW enhanced modules
    print("\nInitializing enhanced detection modules...")
    
    # Object detector (YOLOv8)
    object_detector = ObjectDetector(model_size='n', confidence_threshold=0.5)
    if object_detector.enabled:
        print("✓ Object detection enabled (YOLOv8)")
    else:
        print("✗ Object detection disabled (install ultralytics)")
    
    # Context analyzer
    context_analyzer = ContextAnalyzer()
    print("✓ Context analyzer initialized")
    
    # Adaptive scorer with user calibration
    adaptive_scorer = AdaptiveAttentionScorer(user_id="default")
    if adaptive_scorer.is_calibrated:
        print("✓ Using calibrated thresholds")
    else:
        print("○ Using default thresholds (calibration recommended)")
    
    # Pattern recognizer
    pattern_recognizer = PatternRecognizer(window_size=60)
    print("✓ Pattern recognizer initialized")
    
    # Server reporter (OPTIONAL - disabled by default for standalone use)
    server_reporter = ServerReporter(enabled=False)  # Set to True to enable server integration
    if server_reporter.enabled:
        print("✓ Server reporter enabled")
    
    print("\n" + "=" * 50 + "\n")
    
    # Timing variables
    prev_time = time.perf_counter()
    fps = 0.0
    t_now = time.perf_counter()
    
    # Original attention scorer (for backward compatibility)
    thresholds = adaptive_scorer.get_thresholds()
    Scorer = AttScorer(
        t_now=t_now,
        ear_thresh=thresholds['ear_thresh'],
        gaze_thresh=thresholds['gaze_thresh'],
        roll_thresh=thresholds['roll_thresh'],
        pitch_thresh=thresholds['pitch_thresh'],
        yaw_thresh=thresholds['yaw_thresh'],
        ear_time_thresh=args.ear_time_thresh,
        gaze_time_thresh=args.gaze_time_thresh,
        pose_time_thresh=args.pose_time_thresh,
        verbose=args.verbose,
    )
    
    # Capture video
    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print("Cannot open camera")
        exit()
    
    # State tracking
    last_distracted = False
    last_face_detected = True
    face_not_detected_time = 0.0
    face_detected_time = 0.0
    
    # Enhanced state tracking
    current_activity = ActivityType.UNKNOWN
    distraction_start_time = None
    
    # Notify server to start session
    try:
        requests.post(f"{SERVER_URL}/session/start", json={}, timeout=0.5)
        print(f"Connected to server at {SERVER_URL}")
    except Exception as e:
        print(f"Warning: Could not connect to server at {SERVER_URL}: {e}")
        print("Continuing in standalone mode...")
    
    start_time = time.perf_counter()
    frame_count = 0
    
    print("Detection started. Press 'q' to quit.\n")
    
    while True:
        t_now = time.perf_counter()
        elapsed_time = t_now - prev_time
        prev_time = t_now
        
        if elapsed_time > 0:
            fps = np.round(1 / elapsed_time, 3)
        
        ret, frame = cap.read()
        if not ret:
            print("Can't receive frame from camera")
            break
        
        # Flip frame if from webcam
        if args.camera == 0:
            frame = cv2.flip(frame, 2)
        
        e1 = cv2.getTickCount()
        
        # Convert to grayscale for MediaPipe
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        frame_size = frame.shape[1], frame.shape[0]
        gray = np.expand_dims(gray, axis=2)
        gray = np.concatenate([gray, gray, gray], axis=2)
        
        # Detect faces
        lms = Detector.process(gray).multi_face_landmarks
        face_detected = bool(lms)
        
        # NEW: Detect objects in frame
        detected_objects = object_detector.detect_objects(frame)
        
        # Update face presence timers
        if not face_detected:
            face_not_detected_time += elapsed_time
            face_detected_time = 0.0
        else:
            face_detected_time += elapsed_time
            face_not_detected_time = 0.0
        
        # Sustained face missing/present
        face_missing_state = face_not_detected_time >= 2.5
        face_present_state = face_detected_time >= 2.5
        
        # Initialize metrics
        ear = None
        gaze = None
        roll = None
        pitch = None
        yaw = None
        activity = ActivityType.UNKNOWN
        is_distracted = False
        distraction_severity = 0.0
        
        if lms:
            # Get landmarks
            landmarks = get_landmarks(lms)
            
            # Show eye keypoints
            Eye_det.show_eye_keypoints(
                color_frame=frame, landmarks=landmarks, frame_size=frame_size
            )
            
            # Compute EAR
            ear = Eye_det.get_EAR(landmarks=landmarks)
            
            # Compute PERCLOS
            tired, perclos_score = Scorer.get_rolling_PERCLOS(t_now, ear)
            
            # Compute Gaze Score
            gaze = Eye_det.get_Gaze_Score(
                frame=gray, landmarks=landmarks, frame_size=frame_size
            )
            
            # Compute head pose
            frame_det, roll, pitch, yaw = Head_pose.get_pose(
                frame=frame, landmarks=landmarks, frame_size=frame_size
            )
            
            if frame_det is not None:
                frame = frame_det
            
            # NEW: Add samples to pattern recognizer
            pattern_recognizer.add_sample(gaze, pitch, ear)
            
            # NEW: Analyze context to classify activity
            activity, is_distracted, distraction_severity = context_analyzer.analyze_context(
                t_now=t_now,
                head_pitch=pitch[0] if pitch is not None else None,
                head_yaw=yaw[0] if yaw is not None else None,
                head_roll=roll[0] if roll is not None else None,
                gaze_score=gaze,
                ear_score=ear,
                detected_objects=detected_objects,
                face_detected=face_detected
            )
            
            # NEW: Check for anomalies (spoofing detection)
            if adaptive_scorer.detect_anomaly(ear, gaze, pitch[0] if pitch is not None else None):
                cv2.putText(
                    frame,
                    "WARNING: Unusual pattern detected",
                    (10, frame_size[1] - 20),
                    cv2.FONT_HERSHEY_PLAIN,
                    1,
                    (0, 0, 255),
                    2,
                    cv2.LINE_AA,
                )
            
            # Original scoring (for backward compatibility)
            asleep, looking_away, distracted = Scorer.eval_scores(
                t_now=t_now,
                ear_score=ear,
                gaze_score=gaze,
                head_roll=roll,
                head_pitch=pitch,
                head_yaw=yaw,
            )
            
            # Display metrics
            if ear is not None:
                cv2.putText(frame, f"EAR: {ear:.3f}", (10, 50),
                           cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 1, cv2.LINE_AA)
            
            if gaze is not None:
                cv2.putText(frame, f"Gaze: {gaze:.3f}", (10, 80),
                           cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 1, cv2.LINE_AA)
            
            cv2.putText(frame, f"PERCLOS: {perclos_score:.3f}", (10, 110),
                       cv2.FONT_HERSHEY_PLAIN, 2, (255, 255, 255), 1, cv2.LINE_AA)
            
            # NEW: Display activity and detected objects
            activity_display = activity.replace('_', ' ').title()
            color = (0, 255, 0) if not is_distracted else (0, 165, 255)
            cv2.putText(frame, f"Activity: {activity_display}", (10, 140),
                       cv2.FONT_HERSHEY_PLAIN, 1.5, color, 2, cv2.LINE_AA)
            
            # Display detected objects
            y_offset = 170
            for obj_name, detected in detected_objects.items():
                if detected:
                    cv2.putText(frame, f"+ {obj_name.title()}", (10, y_offset),
                               cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 255), 1, cv2.LINE_AA)
                    y_offset += 20
            
            # Display head angles
            if roll is not None:
                cv2.putText(frame, f"Roll: {roll.round(1)[0]}", (450, 40),
                           cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 1, cv2.LINE_AA)
            if pitch is not None:
                cv2.putText(frame, f"Pitch: {pitch.round(1)[0]}", (450, 70),
                           cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 1, cv2.LINE_AA)
            if yaw is not None:
                cv2.putText(frame, f"Yaw: {yaw.round(1)[0]}", (450, 100),
                           cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 0, 255), 1, cv2.LINE_AA)
            
            # Display warnings
            if tired:
                cv2.putText(frame, "TIRED!", (10, 280),
                           cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
            
            if asleep:
                cv2.putText(frame, "ASLEEP!", (10, 300),
                           cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
            
            if looking_away:
                cv2.putText(frame, "LOOKING AWAY!", (10, 320),
                           cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
            
            # NEW: Context-aware distraction handling
            if is_distracted and activity != ActivityType.THINKING:
                # Ignore brief distractions (micro-breaks)
                if distraction_start_time is None:
                    distraction_start_time = t_now
                
                distraction_duration = t_now - distraction_start_time
                
                # Only flag if sustained (> 5 seconds)
                if distraction_duration > 5.0:
                    severity_text = f"Distracted ({distraction_severity:.0%})"
                    cv2.putText(frame, severity_text, (10, 340),
                               cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
                    
                    # Send to server only if not already sent
                    if not last_distracted:
                        try:
                            requests.post(f"{SERVER_URL}/light",
                                        json={"light_on": True}, timeout=0.75)
                            requests.post(f"{SERVER_URL}/session/edge",
                                        json={"distracted": True}, timeout=0.5)
                        except Exception:
                            pass
                        last_distracted = True
            else:
                # Reset distraction timer
                distraction_start_time = None
                
                if last_distracted:
                    try:
                        requests.post(f"{SERVER_URL}/light",
                                    json={"light_on": False}, timeout=0.75)
                        requests.post(f"{SERVER_URL}/session/edge",
                                    json={"distracted": False}, timeout=0.5)
                    except Exception:
                        pass
                    last_distracted = False
        
        else:
            # No face detected - use context analyzer
            activity, is_distracted, distraction_severity = context_analyzer.analyze_context(
                t_now=t_now,
                head_pitch=None,
                head_yaw=None,
                head_roll=None,
                gaze_score=None,
                ear_score=None,
                detected_objects=detected_objects,
                face_detected=False
            )
        
        # Handle sustained face missing
        if face_missing_state:
            cv2.putText(frame, "FACE NOT DETECTED", (10, 340),
                       cv2.FONT_HERSHEY_PLAIN, 1, (0, 0, 255), 1, cv2.LINE_AA)
            
            if last_face_detected:
                try:
                    requests.post(f"{SERVER_URL}/light",
                                json={"light_on": True}, timeout=0.75)
                    if time.perf_counter() - start_time >= 1.0:
                        requests.post(f"{SERVER_URL}/session/edge",
                                    json={"distracted": True}, timeout=0.5)
                except Exception:
                    pass
                last_face_detected = False
        
        if face_present_state and not last_face_detected:
            try:
                requests.post(f"{SERVER_URL}/light",
                            json={"light_on": False}, timeout=0.75)
                if time.perf_counter() - start_time >= 1.0:
                    requests.post(f"{SERVER_URL}/session/edge",
                                json={"distracted": False}, timeout=0.5)
            except Exception:
                pass
            last_face_detected = True
        
        # Processing time
        e2 = cv2.getTickCount()
        proc_time_frame_ms = ((e2 - e1) / cv2.getTickFrequency()) * 1000
        
        # Display FPS and processing time
        if args.show_fps:
            cv2.putText(frame, f"FPS: {round(fps)}", (10, 400),
                       cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 1)
        
        if args.show_proc_time:
            cv2.putText(frame, f"PROC: {round(proc_time_frame_ms, 0)}ms", (10, 430),
                       cv2.FONT_HERSHEY_PLAIN, 2, (255, 0, 255), 1)
        
        # Show frame
        cv2.imshow("Enhanced Study Focus Tracker - Press 'q' to quit", frame)
        
        # Check for quit
        if cv2.waitKey(20) & 0xFF == ord('q'):
            break
        
        frame_count += 1
    
    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    
    # Finalize session
    try:
        requests.post(f"{SERVER_URL}/session/stop", json={}, timeout=0.5)
        print(f"Session stopped on server at {SERVER_URL}")
    except Exception as e:
        print(f"Warning: Could not notify server of session stop: {e}")
    
    print(f"\nSession ended. Processed {frame_count} frames.")
    
    # Display pattern summary
    pattern_summary = pattern_recognizer.get_pattern_summary()
    print("\nPattern Analysis Summary:")
    print(f"  Reading pattern: {pattern_summary['reading']}")
    print(f"  Thinking pattern: {pattern_summary['thinking']}")
    print(f"  Phone pattern: {pattern_summary['phone']}")
    print(f"  Natural blinks: {pattern_summary['natural_blinks']} ({pattern_summary['blink_count']} detected)")
    print(f"  Micro-movements: {pattern_summary['micro_movements']}")
    print(f"  Engagement score: {pattern_summary['engagement_score']:.2f}")
    
    return


if __name__ == "__main__":
    main()

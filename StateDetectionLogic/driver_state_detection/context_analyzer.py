"""
Context-Aware Analysis Module
Combines face detection, pose, gaze, and object detection to classify user activity
"""

import numpy as np
from typing import Dict, Optional, Tuple
from collections import deque


class ActivityType:
    """Activity classification constants."""
    FOCUSED_STUDYING = "focused_studying"
    READING_BOOK = "reading_book"
    TAKING_NOTES = "taking_notes"
    TYPING = "typing"
    THINKING = "thinking"
    PHONE_DISTRACTION = "phone_distraction"
    DRINKING_WATER = "drinking_water"  # NEW: Drinking water/coffee
    LOOKING_AWAY = "looking_away"
    FACE_MISSING = "face_missing"
    UNKNOWN = "unknown"


class ContextAnalyzer:
    """
    Analyzes context to determine user activity and distraction level.
    Combines multiple signals: head pose, gaze, objects, and temporal patterns.
    """
    
    def __init__(self):
        # Angle thresholds for different activities
        self.READING_PITCH_RANGE = (-45, -25)      # Head down for reading
        self.NOTE_TAKING_PITCH_RANGE = (-50, -30)  # Slightly more down
        self.PHONE_PITCH_THRESHOLD = -60           # Very steep angle
        self.THINKING_GAZE_THRESHOLD = 0.3         # Looking away while thinking
        
        # Time thresholds
        self.MICRO_BREAK_THRESHOLD = 5.0           # Ignore brief glances (seconds)
        self.SUSTAINED_ACTIVITY_THRESHOLD = 3.0    # Confirm activity after 3s
        
        # Activity history for pattern recognition
        self.activity_history = deque(maxlen=30)   # Last 30 frames (~1 second at 30fps)
        self.distraction_start_time = None
        self.current_activity = ActivityType.UNKNOWN
        
    def analyze_context(
        self,
        t_now: float,
        head_pitch: Optional[float],
        head_yaw: Optional[float],
        head_roll: Optional[float],
        gaze_score: Optional[float],
        ear_score: Optional[float],
        detected_objects: Dict[str, bool],
        face_detected: bool
    ) -> Tuple[str, bool, float]:
        """
        Analyze current context and classify activity.
        
        Parameters
        ----------
        t_now : float
            Current timestamp
        head_pitch : float
            Head pitch angle (negative = looking down)
        head_yaw : float
            Head yaw angle
        head_roll : float
            Head roll angle
        gaze_score : float
            Gaze deviation score
        ear_score : float
            Eye aspect ratio
        detected_objects : Dict[str, bool]
            Dictionary of detected objects
        face_detected : bool
            Whether face is detected
            
        Returns
        -------
        activity : str
            Classified activity type
        is_distracted : bool
            Whether user is distracted
        distraction_severity : float
            Severity of distraction (0.0 = none, 1.0 = severe)
        """
        if not face_detected:
            activity = ActivityType.FACE_MISSING
            is_distracted = True
            severity = 0.8
            self.activity_history.append(activity)
            return activity, is_distracted, severity
        
        # Extract object presence
        has_book = detected_objects.get('book', False)
        has_phone = detected_objects.get('cell phone', False)
        has_laptop = detected_objects.get('laptop', False)
        has_bottle = detected_objects.get('bottle', False)
        has_cup = detected_objects.get('cup', False)
        
        # Classify activity based on combined signals
        activity = self._classify_activity(
            head_pitch, head_yaw, gaze_score, ear_score,
            has_book, has_phone, has_laptop, has_bottle, has_cup
        )
        
        # Determine if distracted
        is_distracted, severity = self._evaluate_distraction(
            activity, head_pitch, gaze_score, ear_score
        )
        
        # Update history
        self.activity_history.append(activity)
        self.current_activity = activity
        
        return activity, is_distracted, severity
    
    def _classify_activity(
        self,
        pitch: Optional[float],
        yaw: Optional[float],
        gaze: Optional[float],
        ear: Optional[float],
        has_book: bool,
        has_phone: bool,
        has_laptop: bool,
        has_bottle: bool,
        has_cup: bool
    ) -> str:
        """Classify user activity based on all available signals."""
        
        if pitch is None:
            return ActivityType.UNKNOWN
        
        # Drinking water/coffee: bottle or cup detected with head tilted back
        if (has_bottle or has_cup) and pitch > -15:
            return ActivityType.DRINKING_WATER
        
        # Phone usage: phone detected (any angle) OR very steep angle
        # Lower threshold to catch phone on ear
        if has_phone or pitch < self.PHONE_PITCH_THRESHOLD:
            return ActivityType.PHONE_DISTRACTION
        
        # Reading: book present + reading angle
        if has_book and self.READING_PITCH_RANGE[0] <= pitch <= self.READING_PITCH_RANGE[1]:
            return ActivityType.READING_BOOK
        
        # Note-taking: head down without book/phone/bottle/cup
        if (not has_book and not has_phone and not has_bottle and not has_cup and 
            self.NOTE_TAKING_PITCH_RANGE[0] <= pitch <= self.NOTE_TAKING_PITCH_RANGE[1]):
            return ActivityType.TAKING_NOTES
        
        # Typing: laptop present + slight head down
        if has_laptop and -20 <= pitch <= 0:
            return ActivityType.TYPING
        
        # Thinking: looking away briefly with good posture
        if gaze is not None and gaze > self.THINKING_GAZE_THRESHOLD and abs(pitch) < 20:
            return ActivityType.THINKING
        
        # Looking away: gaze off-center
        if gaze is not None and gaze > 0.25:
            return ActivityType.LOOKING_AWAY
        
        # Default: focused studying
        if abs(pitch) < 25 and (gaze is None or gaze < 0.2):
            return ActivityType.FOCUSED_STUDYING
        
        return ActivityType.UNKNOWN
    
    def _evaluate_distraction(
        self,
        activity: str,
        pitch: Optional[float],
        gaze: Optional[float],
        ear: Optional[float]
    ) -> Tuple[bool, float]:
        """
        Evaluate if current activity constitutes distraction.
        
        Returns
        -------
        is_distracted : bool
        severity : float (0.0 to 1.0)
        """
        # Productive activities are not distractions
        productive_activities = {
            ActivityType.FOCUSED_STUDYING,
            ActivityType.READING_BOOK,
            ActivityType.TAKING_NOTES,
            ActivityType.TYPING,
        }
        
        if activity in productive_activities:
            return False, 0.0
        
        # Drinking water is a brief, acceptable break
        if activity == ActivityType.DRINKING_WATER:
            # Check if drinking for too long (> 10 seconds is suspicious)
            recent_drinking = sum(1 for a in self.activity_history if a == ActivityType.DRINKING_WATER)
            if recent_drinking < 15:  # Less than ~0.5 seconds at 30fps
                return False, 0.0  # Not a distraction
            else:
                return True, 0.2  # Low severity if prolonged
        
        # Thinking is allowed briefly
        if activity == ActivityType.THINKING:
            # Check if thinking for too long
            recent_thinking = sum(1 for a in self.activity_history if a == ActivityType.THINKING)
            if recent_thinking < 8:  # Less than ~0.25 seconds
                return False, 0.1
            else:
                return True, 0.3
        
        # Phone is high severity distraction
        if activity == ActivityType.PHONE_DISTRACTION:
            return True, 0.9
        
        # Face missing is high severity
        if activity == ActivityType.FACE_MISSING:
            return True, 0.8
        
        # Looking away is moderate distraction
        # Count consecutive looking away frames to detect sustained distraction
        if activity == ActivityType.LOOKING_AWAY:
            recent_looking_away = sum(1 for a in self.activity_history if a == ActivityType.LOOKING_AWAY)
            # If looking away for more than 15 frames (~0.5s at 30fps), flag as distracted
            # The main loop will handle the 15-second sustained check
            return True, 0.6
        
        # Unknown activity is low severity
        return True, 0.3
    
    def get_activity_pattern(self) -> Dict[str, float]:
        """
        Get distribution of activities over recent history.
        
        Returns
        -------
        Dict[str, float]
            Percentage of time in each activity
        """
        if not self.activity_history:
            return {}
        
        total = len(self.activity_history)
        pattern = {}
        
        for activity in set(self.activity_history):
            count = sum(1 for a in self.activity_history if a == activity)
            pattern[activity] = count / total
        
        return pattern
    
    def is_sustained_distraction(self, threshold_seconds: float = 3.0, fps: float = 30.0) -> bool:
        """
        Check if distraction has been sustained for threshold duration.
        
        Parameters
        ----------
        threshold_seconds : float
            Minimum duration to consider sustained
        fps : float
            Frames per second
            
        Returns
        -------
        bool
            True if distracted for >= threshold duration
        """
        required_frames = int(threshold_seconds * fps)
        
        if len(self.activity_history) < required_frames:
            return False
        
        # Check last N frames
        recent = list(self.activity_history)[-required_frames:]
        
        distracted_activities = {
            ActivityType.PHONE_DISTRACTION,
            ActivityType.FACE_MISSING,
            ActivityType.LOOKING_AWAY,
        }
        
        distracted_count = sum(1 for a in recent if a in distracted_activities)
        
        # Consider sustained if >80% of frames are distracted
        return distracted_count / required_frames > 0.8
    
    def should_ignore_brief_distraction(self, duration: float) -> bool:
        """Check if distraction is brief enough to ignore (micro-break)."""
        return duration < self.MICRO_BREAK_THRESHOLD

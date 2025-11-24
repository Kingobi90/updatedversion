"""
In-memory session store - no Firebase required.
Direct communication between Python detection and Android app.
"""
from datetime import datetime, timezone
from typing import Optional
import threading

class InMemorySessionStore:
    def __init__(self):
        self.lock = threading.Lock()
        self.session_id = None
        self.started_at = None
        self.distracted_total_ms = 0
        self.interval_count = 0
        self.current_interval_start = None
        self.current_activity = "unknown"
        self.current_severity = 0.0
        self.is_active = False
        
    def start_session(self, user_id=None, username=None):
        with self.lock:
            self.session_id = f"session_{int(datetime.now(timezone.utc).timestamp())}"
            self.started_at = datetime.now(timezone.utc)
            self.distracted_total_ms = 0
            self.interval_count = 0
            self.current_interval_start = None
            self.current_activity = "unknown"
            self.current_severity = 0.0
            self.is_active = True
            return self.session_id
    
    def mark_distracted(self, session_id, start_at=None, activity="unknown", severity=0.5):
        with self.lock:
            if not self.is_active:
                return
            
            # Only start new interval if not already distracted
            if self.current_interval_start is None:
                self.current_interval_start = start_at or datetime.now(timezone.utc)
                self.current_activity = activity
                self.current_severity = severity
    
    def mark_focused(self, session_id, end_at=None):
        with self.lock:
            if not self.is_active:
                return
            
            # Close current interval if one exists
            if self.current_interval_start is not None:
                end_time = end_at or datetime.now(timezone.utc)
                duration_ms = int((end_time - self.current_interval_start).total_seconds() * 1000)
                
                self.distracted_total_ms += duration_ms
                self.interval_count += 1
                self.current_interval_start = None
                self.current_activity = "unknown"
                self.current_severity = 0.0
    
    def get_stats(self):
        with self.lock:
            if not self.is_active or self.started_at is None:
                return None
            
            now = datetime.now(timezone.utc)
            elapsed_ms = int((now - self.started_at).total_seconds() * 1000)
            
            # If currently distracted, add ongoing interval to total
            ongoing_distraction_ms = 0
            if self.current_interval_start is not None:
                ongoing_distraction_ms = int((now - self.current_interval_start).total_seconds() * 1000)
            
            total_distracted = self.distracted_total_ms + ongoing_distraction_ms
            focused_ms = elapsed_ms - total_distracted
            
            if elapsed_ms > 0:
                focus_score = ((1 - float(total_distracted) / elapsed_ms) * 100.0)
            else:
                focus_score = 100.0
            
            return {
                "sessionId": self.session_id,
                "elapsedMs": elapsed_ms,
                "distractedTotalMs": total_distracted,
                "focusedMs": focused_ms,
                "currentFocusScore": round(focus_score, 1),
                "distractionCount": self.interval_count,
                "isDistracted": self.current_interval_start is not None,
                "currentActivity": self.current_activity,
                "currentSeverity": self.current_severity
            }
    
    def stop_session(self, session_id):
        with self.lock:
            # Close any open interval
            if self.current_interval_start is not None:
                self.mark_focused(session_id)
            
            self.is_active = False
            return {
                "sessionId": self.session_id,
                "distractedTotalMs": self.distracted_total_ms,
                "intervalCount": self.interval_count
            }

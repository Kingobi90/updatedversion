"""
Focus Score persistence for server-side sessions in Firestore.

This module defines a server-side collection named "sessionServer" that mirrors the
session data model discussed, without interfering with the mobile app's
"sessions" collection. It lets the local Flask server (or any Python caller)
start/stop a session and record distracted intervals while maintaining running
aggregates (distractedTotalMs, intervalCount) and computing focusScore on stop.

Data model (Firestore):
  - Collection: sessionServer
    Document {sessionId}: {
        userId: string | None
        username: string | None
        startedAt: timestamp
        stoppedAt: timestamp | None
        elapsedMs: number | None
        distractedTotalMs: number     # running total
        intervalCount: number         # running count
        focusScore: number | None
        status: "active" | "completed"
        lastUpdated: timestamp
        # Optional transient field (may be absent):
        # currentIntervalStart: timestamp  # used to hold an open distracted interval
    }

  - Subcollection: sessionServer/{sessionId}/distractedIntervals
    Document {autoId}: {
        startAt: timestamp
        endAt: timestamp
        durationMs: number
        idx: number                    # 1-based index per session
        source: "state-detector"
        createdAt: timestamp
    }

Usage notes:
  1) Install dependencies in your virtualenv:
      pip install firebase-admin google-cloud-firestore

  2) Provide credentials for Admin SDK (DO NOT commit the key):
    - Generate a service account key from Firebase Console
    - Set SERVICE_ACCOUNT_KEY_PATH below to the absolute path of your service account JSON

  3) Call from your Flask server routes:
       from driver_state_detection.focus_score_calculator import SessionServerStore
       store = SessionServerStore()
       session_id = store.start_session(user_id="u123", username="alice")
       store.mark_distracted(session_id)            # on flag true edge
       store.mark_focused(session_id)               # on flag false edge
       store.stop_session(session_id)               # on /stop

  4) This module is side-effect free w.r.t. your app-side Firestore data since it
     writes into the "sessionServer" collection only.

Do NOT import or use this module from Android. Its for server-side use only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple
import os
from pathlib import Path

from dotenv import load_dotenv

import firebase_admin
from firebase_admin import firestore as admin_firestore
from firebase_admin import credentials
from google.cloud import firestore

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

SESSION_COLLECTION = "sessionServer"

# Firebase service account JSON key file path.
# Loaded from .env file (FIREBASE_SERVICE_ACCOUNT_KEY)
_key_from_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY", "firebase-key.json")
if not os.path.isabs(_key_from_env):
    # If relative path, resolve from StateDetectionLogic directory
    SERVICE_ACCOUNT_KEY_PATH = str(Path(__file__).parent.parent / _key_from_env)
else:
    SERVICE_ACCOUNT_KEY_PATH = _key_from_env


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_firebase_initialized() -> None:
    """Initialize Firebase Admin with an explicit service account JSON path.

    Uses SERVICE_ACCOUNT_KEY_PATH defined at module level.
    """
    try:
        firebase_admin.get_app()
        return
    except ValueError:
        pass

    key_path = SERVICE_ACCOUNT_KEY_PATH
    if not key_path:
        raise RuntimeError(
            "SERVICE_ACCOUNT_KEY_PATH is empty. Set it to the absolute path of your "
            "Firebase service account JSON in focus_score_calculator.py."
        )

    cred = credentials.Certificate(key_path)
    firebase_admin.initialize_app(cred)


class SessionServerStore:
    """Server-side Firestore helper for session timing and focus score.

    Methods are idempotent where reasonable; aggregate counters use atomic
    increments to remain consistent under concurrent calls.
    """

    def __init__(self) -> None:
        _ensure_firebase_initialized()
        # The Admin SDK exposes a google.cloud.firestore client
        self._db: admin_firestore.Client = admin_firestore.client()

    # ---------------------- Session lifecycle ----------------------
    def start_session(
        self,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        session_id: Optional[str] = None,
        started_at: Optional[datetime] = None,
    ) -> str:
        """Create a new sessionServer document and return its id.

        If session_id is provided, uses it; otherwise, generates an auto id.
        """
        started_at = started_at or _utcnow()

        doc_ref = (
            self._db.collection(SESSION_COLLECTION).document(session_id)
            if session_id
            else self._db.collection(SESSION_COLLECTION).document()
        )

        doc_ref.set(
            {
                "userId": user_id,
                "username": username,
                "startedAt": started_at,
                "stoppedAt": None,
                "elapsedMs": None,
                "distractedTotalMs": 0,
                "intervalCount": 0,
                "focusScore": None,
                "status": "active",
                "lastUpdated": firestore.SERVER_TIMESTAMP,
            }
        )

        return doc_ref.id

    def stop_session(
        self,
        session_id: str,
        stopped_at: Optional[datetime] = None,
    ) -> Tuple[int, float]:
        """Finalize the session: close any open interval, compute elapsed & focus.

        Returns a tuple of (elapsedMs, focusScore).
        """
        stopped_at = stopped_at or _utcnow()
        session_ref = self._db.collection(SESSION_COLLECTION).document(session_id)

        # Close any open interval prior to finalizing
        self.mark_focused(session_id, end_at=stopped_at)

        snap = session_ref.get()
        data = snap.to_dict() or {}

        started_at: Optional[datetime] = data.get("startedAt")
        distracted_total_ms: int = int(data.get("distractedTotalMs", 0) or 0)

        # calculate total elapsed time for session
        if not started_at:
            # If start missing, consider elapsed 0 to avoid crashes
            elapsed_ms = 0
        else:
            elapsed_ms = int((stopped_at - started_at).total_seconds() * 1000)

        focus_score = ((1 - float(distracted_total_ms) / elapsed_ms) * 100.0) if elapsed_ms > 0 else 0.0

        session_ref.update(
            {
                "stoppedAt": stopped_at,
                "elapsedMs": elapsed_ms,
                "focusScore": focus_score,
                "status": "completed",
                "lastUpdated": firestore.SERVER_TIMESTAMP,
            }
        )

        return elapsed_ms, focus_score

    # ------------------ Distracted flag transitions ------------------
    def mark_distracted(self, session_id: str, start_at: Optional[datetime] = None, 
                       activity: str = "unknown", severity: float = 0.5) -> None:
        """Record the start of a distracted interval (false -> true edge).

        If an interval is already open, this is a no-op.
        
        Parameters
        ----------
        session_id : str
            The session ID
        start_at : datetime, optional
            When the distraction started (defaults to now)
        activity : str, optional
            The activity type (e.g., "phone_distraction", "looking_away")
        severity : float, optional
            Severity level 0.0-1.0
        """
        start_at = start_at or _utcnow()
        session_ref = self._db.collection(SESSION_COLLECTION).document(session_id)
        # Non-transactional, simple guard on currentIntervalStart.
        # Safe enough since edges are serialized per session in our server.
        snap = session_ref.get()
        data = snap.to_dict() or {}

        if data.get("status") == "completed":
            return  # ignore if already finished

        if data.get("currentIntervalStart") is None:
            session_ref.update(
                {
                    "currentIntervalStart": start_at,
                    "currentActivity": activity,
                    "currentSeverity": severity,
                    "lastUpdated": firestore.SERVER_TIMESTAMP,
                }
            )
        # else: interval already open, ignore

    def mark_focused(self, session_id: str, end_at: Optional[datetime] = None) -> Optional[int]:
        """Record the end of a distracted interval (true -> false edge).

        If an interval is open, closes it, writes an interval doc, and updates totals.
        Returns the closed interval duration in ms (or None if nothing to close).
        """
        end_at = end_at or _utcnow()
        session_ref = self._db.collection(SESSION_COLLECTION).document(session_id)
        intervals_col = session_ref.collection("distractedIntervals")

        # Non-transactional close: compute, write interval, then update aggregates.
        snap = session_ref.get()
        data = snap.to_dict() or {}

        if not data or data.get("status") == "completed":
            return None

        start_at = data.get("currentIntervalStart")
        if not start_at:
            return None  # nothing to close

        # Compute duration and next idx
        duration_ms = int((end_at - start_at).total_seconds() * 1000)
        idx = int(data.get("intervalCount", 0) or 0) + 1

        # Get activity and severity from current interval
        activity = data.get("currentActivity", "unknown")
        severity = data.get("currentSeverity", 0.5)
        
        # Create interval document with activity and severity
        interval_ref = intervals_col.document()
        interval_ref.set(
            {
                "startAt": start_at,
                "endAt": end_at,
                "durationMs": duration_ms,
                "idx": idx,
                "activity": activity,
                "severity": severity,
                "source": "state-detector",
                "createdAt": firestore.SERVER_TIMESTAMP,
            }
        )

        # Update aggregates and clear open marker
        session_ref.update(
            {
                "distractedTotalMs": firestore.Increment(duration_ms),
                "intervalCount": firestore.Increment(1),
                "currentIntervalStart": firestore.DELETE_FIELD,
                "currentActivity": firestore.DELETE_FIELD,
                "currentSeverity": firestore.DELETE_FIELD,
                "lastUpdated": firestore.SERVER_TIMESTAMP,
            }
        )

        return duration_ms


# # Optional: tiny self-test when run directly (no external side effects beyond Firestore writes)
# if __name__ == "__main__":
#     store = SessionServerStore()
#     sid = store.start_session(user_id="demo", username="demo-user")
#     store.mark_distracted(sid)
#     # Simulate some work
#     import time as _t
#     _t.sleep(0.2)
#     store.mark_focused(sid)
#     elapsed, score = store.stop_session(sid)
#     print(f"Session {sid} finalized. elapsedMs={elapsed}, focusScore={score:.2f}")

import os
import sys
import subprocess
import time
import atexit
import logging
import threading
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sock import Sock
from driver_state_detection.focus_score_calculator import SessionServerStore

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

app = Flask(__name__)
sock = Sock(app)

logging.getLogger("werkzeug").setLevel(logging.INFO)
app.logger.setLevel(logging.INFO)

proc = None
light_on_state = False
ws_clients = set()  # track connected WebSocket clients
session_store = None  # type: SessionServerStore | None
session_id = None     # type: str | None
session_username = None  # type: str | None
session_username_lock = threading.Lock()


@app.before_request
def _log_endpoint():
    # Minimal, consistent request logging: METHOD PATH
    app.logger.info(f"{request.method} {request.path}")


@app.route('/')
def root():
    return jsonify({
        "status": "ok",
        "endpoints": [
            "/start", 
            "/stop", 
            "/status", 
            "/light", 
            "/ws",
            "/session/start",
            "/session/edge",
            "/session/stop"
        ]
    })


@app.route('/status')
def status():
    global proc
    running = proc is not None and proc.poll() is None
    pid = proc.pid if running else None
    return jsonify({"running": running, "pid": pid})

@app.route('/light', methods=['POST'])
def light():
    global light_on_state
    data = request.get_json(silent=True) or {}

    # Robust parsing of light_on
    val = data.get("light_on", True)
    if isinstance(val, bool):
        light_on_state = val
    elif isinstance(val, str):
        light_on_state = val.lower() == "true"  # Only "true" is True, everything else False
    else:
        light_on_state = bool(val)

    # Minimal log via @before_request already prints the endpoint

    # No database writes here; just broadcast state

    # Broadcast to all connected WebSocket clients as raw string
    for ws in list(ws_clients):
        try:
            ws.send("ON" if light_on_state else "OFF")
        except Exception:
            ws_clients.discard(ws)

    return jsonify({"status": "ok", "light_on": light_on_state})


# -------------------- Focus scoring session APIs (do not affect /start|/stop) --------------------
@app.route('/session/start', methods=['POST'])
def session_start():
    """Initialize a server-side focus scoring session (Firestore) without touching the vision process.

    Idempotent: if a session already exists in-memory, returns the existing sessionId.
    Accepts JSON: {"username": string}
    """
    global session_store, session_id, session_username, session_username_lock
    body = request.get_json(silent=True) or {}
    # user_id = body.get("userId")
    username = body.get("username")
    # If the client did not send username here, fall back to a username previously
    # bound via POST /start (if any). That value is set in /start when a client
    # includes {"username": "..."} in its request body.
    if username is None:
        try:
            with session_username_lock:
                username = session_username
        except Exception:
            username = None
    try:
        if session_store is None or session_id is None:
            store = SessionServerStore()
            sid = store.start_session(username=username)
            session_store, session_id = store, sid
            app.logger.info(f"Created document in Firebase: {session_id}")
            # Minimal log via @before_request already prints the endpoint
        return jsonify({"status": "ok", "sessionId": session_id})
    except Exception as e:
        app.logger.warning(f"/session/start skipped: {e}")
        return jsonify({"status": "skipped", "error": str(e)}), 200


@app.route('/session/edge', methods=['POST'])
def session_edge():
    """Record a distracted/focused edge into Firestore.

    JSON: {"distracted": bool}
    Lazily creates a session if one doesn't exist.
    """
    global session_store, session_id
    data = request.get_json(silent=True) or {}
    distracted = bool(data.get("distracted", False))
    try:
        if session_store is None or session_id is None:
            store = SessionServerStore()
            sid = store.start_session(user_id=None, username=None)
            session_store, session_id = store, sid
            # Minimal log via @before_request already prints the endpoint

        if distracted:
            session_store.mark_distracted(session_id)
        else:
            session_store.mark_focused(session_id)
        return jsonify({"status": "ok", "sessionId": session_id})
    except Exception as e:
        app.logger.warning(f"/session/edge skipped: {e}")
        return jsonify({"status": "skipped", "error": str(e)}), 200


@app.route('/session/stop', methods=['POST'])
def session_stop():
    """Finalize the current focus scoring session: close interval, compute totals & score.

    Does not touch the vision process. Safe to call multiple times; after success, in-memory
    session references are cleared.
    """
    global session_store, session_id
    try:
        if session_store and session_id:
            elapsed_ms, focus = session_store.stop_session(session_id)
            resp = {"status": "ok", "sessionId": session_id, "elapsedMs": elapsed_ms, "focusScore": focus}
        else:
            resp = {"status": "noop"}
    except Exception as e:
        app.logger.warning(f"/session/stop skipped: {e}")
        resp = {"status": "skipped", "error": str(e)}
    finally:
        session_store = None
        session_id = None
    return jsonify(resp)

@app.route('/session/stats', methods=['GET'])
def session_stats():
    """Get real-time session statistics including current focus score."""
    global session_store, session_id
    try:
        if not session_store or not session_id:
            return jsonify({"status": "no_active_session"})
        
        # Get current session data from Firestore
        doc = session_store.db.collection(session_store.collection_name).document(session_id).get()
        if not doc.exists:
            return jsonify({"status": "session_not_found"})
        
        data = doc.to_dict()
        started_at = data.get("startedAt")
        distracted_total_ms = data.get("distractedTotalMs", 0)
        interval_count = data.get("intervalCount", 0)
        
        # Calculate elapsed time
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        if started_at:
            elapsed_ms = int((now - started_at).total_seconds() * 1000)
        else:
            elapsed_ms = 0
        
        # Calculate current focus score
        if elapsed_ms > 0:
            current_focus_score = ((1 - float(distracted_total_ms) / elapsed_ms) * 100.0)
        else:
            current_focus_score = 100.0
        
        # Calculate focused time
        focused_ms = elapsed_ms - distracted_total_ms
        
        return jsonify({
            "status": "ok",
            "sessionId": session_id,
            "elapsedMs": elapsed_ms,
            "distractedTotalMs": distracted_total_ms,
            "focusedMs": focused_ms,
            "currentFocusScore": round(current_focus_score, 1),
            "distractionCount": interval_count,
            "isDistracted": data.get("currentIntervalStart") is not None
        })
    except Exception as e:
        app.logger.error(f"Error getting session stats: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route('/start', methods=['POST'])
def start():
    """
    Starts the driver_state_detection.enhanced_main process if not already running.
    Returns JSON with status and PID if started successfully.
    """
    global proc, light_on_state, session_username, session_username_lock

    # Check if process is already running
    if proc is not None and proc.poll() is None:
        app.logger.info("/start called but process already running (pid=%s)", proc.pid)
        return jsonify({"status": "already running", "pid": proc.pid})

    python_exec = sys.executable
    cmd = [python_exec, "-m", "driver_state_detection.enhanced_main"]
    # Minimal log via @before_request already prints the endpoint

    # Optionally accept JSON {"username": "..."} and bind it so
    # subsequent /session/start requests can implicitly use it.
    try:
        body = request.get_json(silent=True) or {}
        posted_username = body.get("username")
        if posted_username:
            try:
                with session_username_lock:
                    session_username = posted_username
                    app.logger.info(f"Bound username from /start: {session_username}")
            except Exception:
                app.logger.warning("Failed to bind username from /start")
    except Exception:
        # Non-JSON or no body is fine; /start can still be used to just start the process
        pass

    try:
        # Start subprocess
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # isolate child from our tty signals (Ctrl+C)
        )

        # Short delay to catch immediate failures
        time.sleep(0.3)

        if proc.poll() is not None:
            # Process exited immediately
            proc = None
            return jsonify({"status": "failed"}), 500

        # Fail-safe: ensure LED starts OFF
        light_on_state = False
        for ws in list(ws_clients):
            try:
                ws.send("OFF")
            except Exception:
                ws_clients.discard(ws)

        # No database session initialization here

        # Successfully started
    # Minimal log via @before_request already prints the endpoint
        return jsonify({"status": "started", "pid": proc.pid})

    except Exception as e:
        app.logger.exception("Failed to start vision process: %s", e)
        proc = None
        return jsonify({"status": "error", "error": str(e)}), 500



@app.route('/stop', methods=['POST'])
def stop():
    global proc, light_on_state, session_store, session_id
    if proc is None or proc.poll() is not None:
        # Even if process already stopped, finalize any open session
        resp = {"status": "not running"}
        if session_store and session_id:
            try:
                elapsed_ms, focus = session_store.stop_session(session_id)
                resp.update({"sessionId": session_id, "elapsedMs": elapsed_ms, "focusScore": focus})
            except Exception as e:
                resp.update({"sessionFinalizeError": str(e)})
            finally:
                session_store = None
                session_id = None
        return jsonify(resp)

    try:
        proc.terminate()
        proc.wait(timeout=3)
    except Exception:
        proc.kill()
    finally:
        proc = None

        # Ensure LED OFF after stopping
        light_on_state = False
        for ws in list(ws_clients):
            try:
                ws.send("OFF")
            except Exception:
                ws_clients.discard(ws)

    # Always finalize the current focus-scoring session after stopping the process
    if session_store and session_id:
        try:
            elapsed_ms, focus = session_store.stop_session(session_id)
            resp = {"status": "stopped", "sessionId": session_id, "elapsedMs": elapsed_ms, "focusScore": focus}
        except Exception as e:
            resp = {"status": "stopped", "sessionFinalizeError": str(e)}
        finally:
            session_store = None
            session_id = None
        return jsonify(resp)

    return jsonify({"status": "stopped"})


@sock.route('/ws')
def websocket(ws):
    """Handle ESP32 WebSocket clients."""
    app.logger.info("ESP32 connected via WebSocket")
    ws_clients.add(ws)
    try:
        while True:
            msg = ws.receive()
            if msg is None:
                break
            app.logger.info(f"Received from ESP32: {msg}")
    finally:
        ws_clients.discard(ws)
        app.logger.info("ESP32 disconnected")


if __name__ == '__main__':
    # Ensure child process is terminated when the server exits for any reason
    def _cleanup_child():
        global proc
        try:
            if proc is not None and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=2)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        except Exception:
            pass

    atexit.register(_cleanup_child)

    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', '3000'))
    app.run(host=host, port=port)

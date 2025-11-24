package com.example.studytrackerbasictest.databases;

import androidx.annotation.Nullable;
import com.google.firebase.firestore.FirebaseFirestore;
import com.google.firebase.firestore.SetOptions;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class SessionDatabase {

    private final FirebaseFirestore db;

    public SessionDatabase() {
        db = FirebaseFirestore.getInstance();
    }

    // Get next "Session N" for this user
    private void getNextSessionNumber(String username, OnNumberReady listener) {
        db.collection("sessions")
                .whereEqualTo("user", username)
                .get()
                .addOnSuccessListener(snapshot -> {
                    int next = snapshot.size() + 1;
                    listener.onReady(next);
                });
    }

    // Unified save method for Home + Countdown
    public void saveSession(String sessionId,
                            String date,
                            String duration,
                            String username,
                            @Nullable Double focusScore) {

        if (sessionId == null || sessionId.isEmpty()) {
            sessionId = "local_" + System.currentTimeMillis();
        }

        String finalSessionId = sessionId;

        getNextSessionNumber(username, nextIndex -> {

            Map<String, Object> data = new HashMap<>();
            data.put("user", username);
            data.put("date", date);
            data.put("duration", duration);
            data.put("name", "Session " + nextIndex);

            if (focusScore != null) {
                data.put("focusScore", focusScore);
            }

            db.collection("sessions")
                    .document(finalSessionId)
                    .set(data, SetOptions.merge())
                    .addOnSuccessListener(aVoid -> {
                        android.util.Log.d("SessionDatabase", "✅ Session saved to Firebase: " + finalSessionId);
                    })
                    .addOnFailureListener(e -> {
                        android.util.Log.e("SessionDatabase", "❌ Failed to save session: " + e.getMessage());
                    });
        });
    }

    // Get all sessions for AnalyticsFragment
    public void getSessionsForUser(String username, OnSessionsLoadedListener listener) {
        db.collection("sessions")
                .whereEqualTo("user", username)
                .get()
                .addOnSuccessListener(qs -> {
                    List<Map<String, Object>> list = new ArrayList<>();
                    for (var doc : qs.getDocuments()) {
                        list.add(doc.getData());
                    }
                    listener.onSessionsLoaded(list);
                });
    }

    public interface OnSessionsLoadedListener {
        void onSessionsLoaded(List<Map<String, Object>> sessions);
    }

    private interface OnNumberReady {
        void onReady(int index);
    }
}

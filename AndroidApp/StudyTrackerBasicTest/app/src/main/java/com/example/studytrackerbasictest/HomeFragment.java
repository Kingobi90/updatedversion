package com.example.studytrackerbasictest;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.util.Log;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.fragment.app.Fragment;

import com.example.studytrackerbasictest.databases.SessionDatabase;

import org.json.JSONObject;

import java.io.IOException;
import java.util.Locale;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

public class HomeFragment extends Fragment {

    OkHttpClient client;
    String BASE_URL = "http://10.0.2.2:3000";

    TextView welcomeText, timerText, statusText, todayTimeValue, totalSessionsValue;
    Button toggleBtn, viewStatsBtn, achievementsBtn;

    String username;
    String currentSessionId = null;

    private Handler handler = new Handler();
    private boolean isRunning = false;
    private int seconds = 0;
    private WebSocket webSocket;

    static final String PREFS_NAME = "AppPrefs";
    static final String KEY_IP = "server_ip";

    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup container, Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_home, container, false);

        welcomeText = v.findViewById(R.id.welcomeText);
        timerText   = v.findViewById(R.id.timerText);
        toggleBtn   = v.findViewById(R.id.toggleBtn);
        statusText  = v.findViewById(R.id.statusText);
        todayTimeValue = v.findViewById(R.id.todayTimeValue);
        totalSessionsValue = v.findViewById(R.id.totalSessionsValue);
        viewStatsBtn = v.findViewById(R.id.viewStatsBtn);
        achievementsBtn = v.findViewById(R.id.achievementsBtn);

        username = getActivity().getIntent().getStringExtra("username");
        if (username != null)
            welcomeText.setText("Welcome, " + username + "!");

        SharedPreferences prefs = getActivity().getSharedPreferences(PREFS_NAME, getActivity().MODE_PRIVATE);
        String savedIp = prefs.getString(KEY_IP, "");
        if (!savedIp.isEmpty()) BASE_URL = "http://" + savedIp + ":3000";

        client = new OkHttpClient();
        
        // Load stats
        loadStats();

        viewStatsBtn.setOnClickListener(v1 -> {
            Intent statsIntent = new Intent(getContext(), StatsActivity.class);
            statsIntent.putExtra("username", username);
            startActivity(statsIntent);
        });

        achievementsBtn.setOnClickListener(v1 -> {
            Intent achievementsIntent = new Intent(getContext(), AchievementsActivity.class);
            startActivity(achievementsIntent);
        });

        toggleBtn.setOnClickListener(vw -> {
            if (!isRunning) {
                // Go to Countdown Fragment to select duration
                if (getActivity() != null) {
                    ((MainActivity) getActivity()).navigateToCountdown();
                }
            } else {
                sendRequest("/stop");
                stopForegroundService();

                String duration = String.format(Locale.getDefault(), "%02d:%02d", seconds / 60, seconds % 60);
                String date = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(new java.util.Date());
                seconds = 0;

                stopFocusSessionAndSave(date, duration, username);

                isRunning = false;
                toggleBtn.setText("Start");
                toggleBtn.setBackgroundResource(R.drawable.round_button_green);
            }
        });

        return v;
    }

    // ---------- Timer ----------
    private void startTimer() {
        isRunning = true;
        seconds = 0;
        timerText.setText("Running: 00:00");
        handler.postDelayed(timerRunnable, 1000);
    }

    private void stopTimer() {
        isRunning = false;
        handler.removeCallbacks(timerRunnable);
        timerText.setText("");
    }

    private final Runnable timerRunnable = new Runnable() {
        @Override public void run() {
            if (isRunning) {
                seconds++;
                timerText.setText(String.format("Running: %02d:%02d", seconds / 60, seconds % 60));
                handler.postDelayed(this, 1000);
            }
        }
    };

    // ---------- Flask start ----------
    private void sendRequest(String endpoint) {
        MediaType JSON = MediaType.parse("application/json; charset=utf-8");

        String bodyText = "{}";
        if (endpoint.equals("/start")) {
            JSONObject obj = new JSONObject();
            try { obj.put("username", username); } catch (Exception ignored) {}
            bodyText = obj.toString();
        }

        Request request = new Request.Builder()
                .url(BASE_URL + endpoint)
                .post(RequestBody.create(bodyText, JSON))
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {}
            @Override public void onResponse(Call call, Response response) {}
        });
    }

    private void startFocusSession(String username) {
        MediaType JSON = MediaType.parse("application/json; charset=utf-8");
        String body = "{\"username\":\"" + username + "\"}";

        Request request = new Request.Builder()
                .url(BASE_URL + "/session/start")
                .post(RequestBody.create(body, JSON))
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {}

            @Override public void onResponse(Call call, Response response) throws IOException {
                try {
                    String responseBody = response.body().string();
                    Log.d("HomeFragment", "Server response: " + responseBody);
                    JSONObject json = new JSONObject(responseBody);
                    currentSessionId = json.optString("sessionId", null);
                    Log.d("HomeFragment", "✅ Session started with ID: " + currentSessionId);
                } catch (Exception e) {
                    Log.e("HomeFragment", "❌ Failed to parse session start response: " + e.getMessage());
                }
            }
        });
    }

    private void stopFocusSessionAndSave(String date, String duration, String username) {

        Request request = new Request.Builder()
                .url(BASE_URL + "/session/stop")
                .post(RequestBody.create("{}", MediaType.parse("application/json; charset=utf-8")))
                .build();

        client.newCall(request).enqueue(new Callback() {

            @Override public void onFailure(Call call, IOException e) {
                SessionDatabase db = new SessionDatabase();
                db.saveSession(currentSessionId, date, duration, username, null);
            }

            @Override public void onResponse(Call call, Response response) throws IOException {
                Double focusScore = null;

                try {
                    String responseBody = response.body().string();
                    Log.d("HomeFragment", "Stop response: " + responseBody);
                    JSONObject json = new JSONObject(responseBody);
                    if (json.has("focusScore")) {
                        focusScore = json.getDouble("focusScore");
                        Log.d("HomeFragment", "✅ Focus score received: " + focusScore);
                    }
                } catch (Exception e) {
                    Log.e("HomeFragment", "❌ Failed to parse stop response: " + e.getMessage());
                }

                Log.d("HomeFragment", "Saving session - ID: " + currentSessionId + ", User: " + username + ", Score: " + focusScore);
                SessionDatabase db = new SessionDatabase();
                db.saveSession(currentSessionId, date, duration, username, focusScore);

                // Show completion notification
                if (getContext() != null) {
                    NotificationHelper.showSessionComplete(getContext(), duration, focusScore);
                    // Check for achievements
                    AchievementManager.checkAndNotifyAchievements(getContext(), username);
                }

                currentSessionId = null;
            }
        });
    }

    private void startForegroundService() {
        if (getContext() != null) {
            Intent serviceIntent = new Intent(getContext(), SessionForegroundService.class);
            serviceIntent.setAction("START");
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                getContext().startForegroundService(serviceIntent);
            } else {
                getContext().startService(serviceIntent);
            }
        }
    }

    private void stopForegroundService() {
        if (getContext() != null) {
            Intent serviceIntent = new Intent(getContext(), SessionForegroundService.class);
            serviceIntent.setAction("STOP");
            getContext().startService(serviceIntent);
        }
    }

    private void connectToDistractionWebSocket() {
        SharedPreferences prefs = getActivity().getSharedPreferences(PREFS_NAME, getActivity().MODE_PRIVATE);
        boolean alertsEnabled = prefs.getBoolean("distraction_alerts", true);
        
        if (!alertsEnabled) return;

        String wsUrl = BASE_URL.replace("http://", "ws://") + "/ws";
        Request request = new Request.Builder().url(wsUrl).build();

        webSocket = client.newWebSocket(request, new WebSocketListener() {
            @Override
            public void onMessage(WebSocket ws, String text) {
                // "ON" = distracted, "OFF" = focused
                if ("ON".equals(text) && getContext() != null) {
                    NotificationHelper.showDistractionAlert(getContext());
                }
            }

            @Override
            public void onFailure(WebSocket ws, Throwable t, okhttp3.Response response) {
                // Connection failed, ignore
            }
        });
    }

    private void disconnectWebSocket() {
        if (webSocket != null) {
            webSocket.close(1000, "Session ended");
            webSocket = null;
        }
    }

    private void loadStats() {
        if (username == null || username.isEmpty()) return;

        SessionDatabase db = new SessionDatabase();
        db.getSessionsForUser(username, sessions -> {
            int totalSessions = sessions.size();
            int todayMinutes = 0;
            String today = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).format(new java.util.Date());

            for (var session : sessions) {
                String date = (String) session.get("date");
                String duration = (String) session.get("duration");
                
                if (duration != null) {
                    String[] parts = duration.split(":");
                    if (parts.length == 2) {
                        int minutes = Integer.parseInt(parts[0]);
                        int secs = Integer.parseInt(parts[1]);
                        
                        if (today.equals(date)) {
                            todayMinutes += minutes;
                        }
                    }
                }
            }

            int todayHours = todayMinutes / 60;
            int todayMins = todayMinutes % 60;

            if (getActivity() != null) {
                getActivity().runOnUiThread(() -> {
                    totalSessionsValue.setText(String.valueOf(totalSessions));
                    todayTimeValue.setText(todayHours + "h " + todayMins + "m");
                });
            }
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        loadStats();
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        disconnectWebSocket();
    }
}

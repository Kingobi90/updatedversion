package com.example.studytrackerbasictest;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.Chronometer;
import android.widget.TextView;

import androidx.annotation.Nullable;
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

public class UntimedSessionFragment extends Fragment {

    private Chronometer chronometer;
    private Button startStopBtn;
    private TextView statusText;

    private boolean isRunning = false;
    private long startTimeMs = 0;
    private long pauseOffset = 0;

    private String username;
    private String currentSessionId = null;

    private final OkHttpClient client = new OkHttpClient();
    private static String BASE_URL = "http://10.0.2.2:3000";

    static final String PREFS_NAME = "AppPrefs";
    static final String KEY_IP = "server_ip";

    @Nullable
    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup parent, Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_untimed_session, parent, false);

        username = getActivity().getIntent().getStringExtra("username");

        chronometer = v.findViewById(R.id.chronometer);
        startStopBtn = v.findViewById(R.id.startStopBtn);
        statusText = v.findViewById(R.id.statusText);

        setupStartStopButton();

        SharedPreferences prefs = getActivity().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        String savedIp = prefs.getString(KEY_IP, "");
        if (!savedIp.isEmpty()) BASE_URL = "http://" + savedIp + ":3000";

        return v;
    }

    private void setupStartStopButton() {
        startStopBtn.setOnClickListener(v -> {
            if (!isRunning) {
                startSession();
            } else {
                stopSession();
            }
        });
    }

    private void startSession() {
        isRunning = true;
        startTimeMs = System.currentTimeMillis();
        
        chronometer.setBase(SystemClock.elapsedRealtime() - pauseOffset);
        chronometer.start();

        startStopBtn.setText("Stop Session");
        startStopBtn.setBackgroundTintList(getResources().getColorStateList(R.color.red_primary));
        statusText.setText("Session in progress...");
        statusText.setTextColor(getResources().getColor(R.color.green_primary));

        sendRequest("/start");
        startFocusSession(username);
    }

    private void stopSession() {
        isRunning = false;
        
        chronometer.stop();
        pauseOffset = SystemClock.elapsedRealtime() - chronometer.getBase();

        startStopBtn.setText("Start Untimed Session");
        startStopBtn.setBackgroundTintList(getResources().getColorStateList(R.color.green_primary));
        statusText.setText("Session stopped");
        statusText.setTextColor(getResources().getColor(R.color.red_primary));

        // Calculate elapsed time
        long elapsedMs = pauseOffset;
        int mins = (int) (elapsedMs / 1000) / 60;
        int secs = (int) (elapsedMs / 1000) % 60;

        String duration = String.format(Locale.getDefault(), "%02d:%02d", mins, secs);
        String date = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                .format(new java.util.Date());

        stopFocusSessionAndSave(date, duration, username);
        sendRequest("/stop");

        // Reset chronometer
        pauseOffset = 0;
        chronometer.setBase(SystemClock.elapsedRealtime());
    }

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

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                try {
                    JSONObject json = new JSONObject(response.body().string());
                    currentSessionId = json.optString("sessionId", null);
                } catch (Exception ignored) {}
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

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                Double focusScore = null;

                try {
                    JSONObject json = new JSONObject(response.body().string());
                    if (json.has("focusScore"))
                        focusScore = json.getDouble("focusScore");
                } catch (Exception ignored) {}

                SessionDatabase db = new SessionDatabase();
                db.saveSession(currentSessionId, date, duration, username, focusScore);

                // Show completion notification
                if (getContext() != null) {
                    NotificationHelper.showSessionComplete(getContext(), duration, focusScore);
                    AchievementManager.checkAndNotifyAchievements(getContext(), username);
                }

                currentSessionId = null;
            }
        });
    }

    @Override
    public void onPause() {
        super.onPause();
        // If session is running when user leaves, keep it running
        // The chronometer will continue in background
    }

    @Override
    public void onResume() {
        super.onResume();
        // Restore state if needed
    }
}

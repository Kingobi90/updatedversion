package com.example.studytrackerbasictest;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.CountDownTimer;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.NumberPicker;
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


public class CountdownFragment extends Fragment {

    private NumberPicker minPicker;
    private Button preset25, preset45, preset60;
    private Button startBtn;
    private TextView timerDisplay;

    private CountDownTimer countDownTimer;
    private boolean isRunning = false;
    private long timeLeftMs = 0;

    private String username;
    private String currentSessionId = null;

    private final OkHttpClient client = new OkHttpClient();
    private static String BASE_URL = "http://10.0.2.2:3000";

    static final String PREFS_NAME = "AppPrefs";
    static final String KEY_IP = "server_ip";

    @Nullable
    @Override
    public View onCreateView(LayoutInflater inflater, ViewGroup parent, Bundle savedInstanceState) {
        View v = inflater.inflate(R.layout.fragment_countdown, parent, false);

        username = getActivity().getIntent().getStringExtra("username");

        minPicker = v.findViewById(R.id.minPicker);
        preset25 = v.findViewById(R.id.preset25);
        preset45 = v.findViewById(R.id.preset45);
        preset60 = v.findViewById(R.id.preset60);
        startBtn = v.findViewById(R.id.startCountdownBtn);
        timerDisplay = v.findViewById(R.id.timerDisplay);

        setupPicker();
        setupPresets();
        setupStartButton();
        
        // Initialize timer display
        updateTimerDisplay(25 * 60 * 1000);

        SharedPreferences prefs = getActivity().getSharedPreferences(PREFS_NAME, getActivity().MODE_PRIVATE);
        String savedIp = prefs.getString(KEY_IP, "");
        if (!savedIp.isEmpty()) BASE_URL = "http://" + savedIp + ":3000";

        return v;
    }

    private void setupPicker() {
        minPicker.setMinValue(1);
        minPicker.setMaxValue(180);
        minPicker.setValue(25);
    }

    private void setupPresets() {
        preset25.setOnClickListener(v -> {
            minPicker.setValue(25);
            updateTimerDisplay(25 * 60 * 1000);
        });
        preset45.setOnClickListener(v -> {
            minPicker.setValue(45);
            updateTimerDisplay(45 * 60 * 1000);
        });
        preset60.setOnClickListener(v -> {
            minPicker.setValue(60);
            updateTimerDisplay(60 * 60 * 1000);
        });
    }

    private void setupStartButton() {
        startBtn.setOnClickListener(v -> {
            if (!isRunning) startCountdown();
            else stopCountdown();
        });
    }

    private void startCountdown() {
        int minutes = minPicker.getValue();
        timeLeftMs = minutes * 60 * 1000L;

        updateTimerDisplay(timeLeftMs);
        startBtn.setText("Stop");
        startBtn.setBackgroundTintList(getResources().getColorStateList(R.color.red_primary));

        isRunning = true;

        sendRequest("/start");
        startFocusSession(username);
        scheduleBreakReminder(timeLeftMs);

        countDownTimer = new CountDownTimer(timeLeftMs, 1000) {
            @Override
            public void onTick(long millisUntilFinished) {
                timeLeftMs = millisUntilFinished;
                updateTimerDisplay(millisUntilFinished);
            }

            @Override
            public void onFinish() {
                stopCountdown();
            }
        }.start();
    }

    private void stopCountdown() {
        if (countDownTimer != null) countDownTimer.cancel();

        startBtn.setText("Start Focus Session");
        startBtn.setBackgroundTintList(getResources().getColorStateList(R.color.green_primary));

        boolean wasFullDuration = (timeLeftMs == 0);

        isRunning = false;

        // Calculate elapsed time
        long originalMs = minPicker.getValue() * 60L * 1000L;
        long elapsedMs = originalMs - timeLeftMs;

        if (elapsedMs < 0) elapsedMs = 0;  // safety

        int mins = (int) (elapsedMs / 1000) / 60;
        int secs = (int) (elapsedMs / 1000) % 60;

        // duration in MM:SS (e.g. 00:40)
        String duration = String.format(Locale.getDefault(), "%02d:%02d", mins, secs);

        String date = new java.text.SimpleDateFormat("yyyy-MM-dd", Locale.getDefault())
                .format(new java.util.Date());

        // Save as session even if stopped early
        stopFocusSessionAndSave(date, duration, username);
        sendRequest("/stop");
    }


    private String formatTime(long ms) {
        int mins = (int) (ms / 1000) / 60;
        int secs = (int) (ms / 1000) % 60;
        return String.format(Locale.getDefault(), "%02d:%02d", mins, secs);
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

    private void scheduleBreakReminder(long durationMs) {
        SharedPreferences prefs = requireActivity().getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        boolean breakRemindersEnabled = prefs.getBoolean("break_reminders", true);
        
        if (!breakRemindersEnabled || getContext() == null) return;

        AlarmManager alarmManager = (AlarmManager) getContext().getSystemService(Context.ALARM_SERVICE);
        if (alarmManager == null) return;

        Intent intent = new Intent(getContext(), BreakReminderReceiver.class);
        PendingIntent pendingIntent = PendingIntent.getBroadcast(
                getContext(),
                3001,
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        long triggerTime = System.currentTimeMillis() + durationMs;
        
        try {
            alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP,
                    triggerTime,
                    pendingIntent
            );
        } catch (SecurityException e) {
            // Fallback if exact alarm permission not granted
            alarmManager.set(AlarmManager.RTC_WAKEUP, triggerTime, pendingIntent);
        }
    }

    private void updateTimerDisplay(long milliseconds) {
        int minutes = (int) (milliseconds / 1000) / 60;
        int seconds = (int) (milliseconds / 1000) % 60;
        timerDisplay.setText(String.format(Locale.getDefault(), "%02d:%02d", minutes, seconds));
    }

}

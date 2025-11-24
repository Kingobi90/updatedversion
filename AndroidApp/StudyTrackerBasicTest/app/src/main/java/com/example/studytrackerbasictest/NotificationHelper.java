package com.example.studytrackerbasictest;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.RingtoneManager;
import android.os.Build;

import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;

public class NotificationHelper {

    // Channel IDs
    public static final String CHANNEL_SESSION = "session_notifications";
    public static final String CHANNEL_DISTRACTION = "distraction_alerts";
    public static final String CHANNEL_REMINDER = "study_reminders";
    public static final String CHANNEL_ACHIEVEMENT = "achievements";

    // Notification IDs
    public static final int NOTIFICATION_SESSION_ACTIVE = 1001;
    public static final int NOTIFICATION_DISTRACTION = 2001;
    public static final int NOTIFICATION_BREAK = 3001;
    public static final int NOTIFICATION_DAILY_REMINDER = 4001;
    public static final int NOTIFICATION_SESSION_COMPLETE = 5001;

    public static void createNotificationChannels(Context context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = context.getSystemService(NotificationManager.class);

            // 1. Session Channel (High priority, sound)
            NotificationChannel sessionChannel = new NotificationChannel(
                    CHANNEL_SESSION,
                    "Study Sessions",
                    NotificationManager.IMPORTANCE_HIGH
            );
            sessionChannel.setDescription("Active session tracking and completion");
            sessionChannel.enableVibration(true);

            // 2. Distraction Channel (High priority, heads-up)
            NotificationChannel distractionChannel = new NotificationChannel(
                    CHANNEL_DISTRACTION,
                    "Focus Alerts",
                    NotificationManager.IMPORTANCE_HIGH
            );
            distractionChannel.setDescription("Real-time distraction alerts");
            distractionChannel.enableVibration(true);

            // 3. Reminder Channel (Default priority)
            NotificationChannel reminderChannel = new NotificationChannel(
                    CHANNEL_REMINDER,
                    "Study Reminders",
                    NotificationManager.IMPORTANCE_DEFAULT
            );
            reminderChannel.setDescription("Scheduled study and break reminders");

            // 4. Achievement Channel (Low priority, no sound)
            NotificationChannel achievementChannel = new NotificationChannel(
                    CHANNEL_ACHIEVEMENT,
                    "Achievements",
                    NotificationManager.IMPORTANCE_LOW
            );
            achievementChannel.setDescription("Milestones and achievements");
            achievementChannel.enableVibration(false);

            manager.createNotificationChannel(sessionChannel);
            manager.createNotificationChannel(distractionChannel);
            manager.createNotificationChannel(reminderChannel);
            manager.createNotificationChannel(achievementChannel);
        }
    }

    public static void showDistractionAlert(Context context) {
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent, PendingIntent.FLAG_IMMUTABLE
        );
        
        // Auto-dismiss after 7 seconds
        long autoCancel = System.currentTimeMillis() + 7000;

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_DISTRACTION)
                .setSmallIcon(R.drawable.outline_display_settings_24)
                .setContentTitle("⚠️ Distraction Detected!")
                .setContentText("You seem distracted. Get back to work!")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setVibrate(new long[]{0, 500, 200, 500})
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setContentIntent(pendingIntent);

        NotificationManagerCompat notificationManager = NotificationManagerCompat.from(context);
        notificationManager.notify(NOTIFICATION_DISTRACTION, builder.build());
        
        // Auto-cancel after 7 seconds
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
            notificationManager.cancel(NOTIFICATION_DISTRACTION);
        }, 7000);
    }

    public static void showSessionComplete(Context context, String duration, Double focusScore) {
        String scoreText = focusScore != null
                ? String.format("Focus: %.0f%%", focusScore)
                : "Focus: N/A";

        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent, PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_SESSION)
                .setSmallIcon(R.drawable.outline_home_24)
                .setContentTitle("✅ Session Completed!")
                .setContentText(duration + " • " + scoreText)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setTimeoutAfter(10000) // Auto-dismiss after 10 seconds
                .setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))
                .setContentIntent(pendingIntent)
                .setStyle(new NotificationCompat.BigTextStyle()
                        .bigText("Great job! You completed a " + duration + " session with " + scoreText));

        NotificationManagerCompat.from(context).notify(NOTIFICATION_SESSION_COMPLETE, builder.build());
    }

    public static void showBreakReminder(Context context) {
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent, PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_REMINDER)
                .setSmallIcon(R.drawable.count_down)
                .setContentTitle("☕ Time for a Break!")
                .setContentText("You've earned it. Rest for 5 minutes.")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setTimeoutAfter(15000) // Auto-dismiss after 15 seconds
                .setSound(RingtoneManager.getDefaultUri(RingtoneManager.TYPE_NOTIFICATION))
                .setContentIntent(pendingIntent);

        NotificationManagerCompat.from(context).notify(NOTIFICATION_BREAK, builder.build());
    }

    public static void showDailyReminder(Context context) {
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent, PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_REMINDER)
                .setSmallIcon(R.drawable.outline_home_24)
                .setContentTitle("📚 Time to Study!")
                .setContentText("You haven't studied today. Start a session now!")
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent);

        NotificationManagerCompat.from(context).notify(NOTIFICATION_DAILY_REMINDER, builder.build());
    }

    public static void showAchievement(Context context, String title, String message) {
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent, PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_ACHIEVEMENT)
                .setSmallIcon(R.drawable.outline_analytics_24)
                .setContentTitle(title)
                .setContentText(message)
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(message));

        NotificationManagerCompat.from(context).notify((int) System.currentTimeMillis(), builder.build());
    }

    public static void showWarning(Context context, String title, String message) {
        Intent intent = new Intent(context, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 0, intent, PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(context, CHANNEL_DISTRACTION)
                .setSmallIcon(R.drawable.outline_display_settings_24)
                .setContentTitle(title)
                .setContentText(message)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setVibrate(new long[]{0, 500, 200, 500})
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setContentIntent(pendingIntent)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(message));

        NotificationManagerCompat notificationManager = NotificationManagerCompat.from(context);
        notificationManager.notify(NOTIFICATION_DISTRACTION, builder.build());
        
        // Auto-cancel after 7 seconds
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
            notificationManager.cancel(NOTIFICATION_DISTRACTION);
        }, 7000);
    }
}

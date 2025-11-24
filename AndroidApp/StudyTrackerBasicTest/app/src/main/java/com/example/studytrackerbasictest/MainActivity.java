package com.example.studytrackerbasictest;

import android.Manifest;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;

import androidx.activity.EdgeToEdge;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.core.content.ContextCompat;
import androidx.fragment.app.Fragment;

import com.google.android.material.bottomnavigation.BottomNavigationView;

public class MainActivity extends AppCompatActivity {

    BottomNavigationView bottomNavigation;
    private ActivityResultLauncher<String> requestPermissionLauncher;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);

        // Initialize notification channels
        NotificationHelper.createNotificationChannels(this);

        // Request notification permission for Android 13+
        requestPermissionLauncher = registerForActivityResult(
                new ActivityResultContracts.RequestPermission(),
                isGranted -> {
                    // Permission granted or denied
                }
        );

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                requestPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS);
            }
        }

        // Toolbar
        Toolbar toolbar = findViewById(R.id.mainToolbar);
        setSupportActionBar(toolbar);

        bottomNavigation = findViewById(R.id.bottomNavigation);

        // Default: Home tab
        if (savedInstanceState == null) {
            loadFragment(new HomeFragment());
        }

        bottomNavigation.setOnItemSelectedListener(item -> {
            Fragment selected = null;
            int id = item.getItemId();

            if (id == R.id.nav_home) {
                selected = new HomeFragment();
            } else if (id == R.id.nav_analytics) {
                selected = new AnalyticsFragment();
            } else if (id == R.id.nav_countdown) {
                selected = new CountdownFragment();
            } else if (id == R.id.nav_untimed) {
                selected = new UntimedSessionFragment();
            } else if (id == R.id.nav_settings) {
                selected = new SettingsFragment();
            }

            if (selected != null) {
                loadFragment(selected);
            }
            return true;
        });
    }

    private void loadFragment(Fragment fragment) {
        getSupportFragmentManager()
                .beginTransaction()
                .replace(R.id.nav_host_fragment, fragment)
                .commit();
    }

    public void navigateToCountdown() {
        bottomNavigation.setSelectedItemId(R.id.nav_countdown);
        loadFragment(new CountdownFragment());
    }
}

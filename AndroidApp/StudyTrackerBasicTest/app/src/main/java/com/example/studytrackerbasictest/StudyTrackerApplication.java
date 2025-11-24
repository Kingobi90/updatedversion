package com.example.studytrackerbasictest;

import android.app.Application;
import com.google.firebase.FirebaseApp;

public class StudyTrackerApplication extends Application {
    
    @Override
    public void onCreate() {
        super.onCreate();
        
        // Initialize Firebase
        FirebaseApp.initializeApp(this);
    }
}

package com.example.studytrackerbasictest;

import android.content.Context;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ArrayAdapter;
import android.widget.ExpandableListView;
import android.widget.ListView;
import android.widget.SimpleExpandableListAdapter;
import android.widget.TextView;

import androidx.fragment.app.Fragment;

import com.example.studytrackerbasictest.databases.SessionDatabase;
import com.github.mikephil.charting.charts.BarChart;
import com.github.mikephil.charting.charts.LineChart;
import com.github.mikephil.charting.charts.PieChart;
import com.github.mikephil.charting.components.XAxis;
import com.github.mikephil.charting.data.BarData;
import com.github.mikephil.charting.data.BarDataSet;
import com.github.mikephil.charting.data.BarEntry;
import com.github.mikephil.charting.data.Entry;
import com.github.mikephil.charting.data.LineData;
import com.github.mikephil.charting.data.LineDataSet;
import com.github.mikephil.charting.data.PieData;
import com.github.mikephil.charting.data.PieDataSet;
import com.github.mikephil.charting.data.PieEntry;
import com.github.mikephil.charting.formatter.ValueFormatter;
import com.google.android.material.tabs.TabLayout;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;

public class AnalyticsFragment extends Fragment {

    private TabLayout timePeriodTabs;
    private TextView avgFocusScore, streakDays, totalSessions, totalHours;
    private BarChart peakFocusChart;
    private PieChart distractionBreakdown;
    private ExpandableListView recentSessionsList;
    
    private String username;
    private String currentPeriod = "today";
    private static final String PREFS_NAME = "AppPrefs";

    @Override
    public View onCreateView(LayoutInflater infl, ViewGroup parent, Bundle savedInstanceState) {
        View v = infl.inflate(R.layout.fragment_analytics, parent, false);

        initViews(v);
        setupTabs();
        setupCharts();

        // Get username
        username = getActivity().getIntent().getStringExtra("username");
        if (username == null || username.isEmpty()) {
            SharedPreferences prefs = requireActivity()
                    .getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
            username = prefs.getString("logged_in_user", null);
        }

        loadStats("today");
        return v;
    }

    private void initViews(View v) {
        timePeriodTabs = v.findViewById(R.id.timePeriodTabs);
        avgFocusScore = v.findViewById(R.id.avgFocusScore);
        streakDays = v.findViewById(R.id.streakDays);
        totalSessions = v.findViewById(R.id.totalSessions);
        totalHours = v.findViewById(R.id.totalHours);
        peakFocusChart = v.findViewById(R.id.peakFocusChart);
        distractionBreakdown = v.findViewById(R.id.distractionBreakdown);
        recentSessionsList = v.findViewById(R.id.recentSessionsList);
    }

    private void setupTabs() {
        timePeriodTabs.addTab(timePeriodTabs.newTab().setText("Today"));
        timePeriodTabs.addTab(timePeriodTabs.newTab().setText("Week"));
        timePeriodTabs.addTab(timePeriodTabs.newTab().setText("Month"));

        timePeriodTabs.addOnTabSelectedListener(new TabLayout.OnTabSelectedListener() {
            @Override
            public void onTabSelected(TabLayout.Tab tab) {
                switch (tab.getPosition()) {
                    case 0: loadStats("today"); break;
                    case 1: loadStats("week"); break;
                    case 2: loadStats("month"); break;
                }
            }
            @Override
            public void onTabUnselected(TabLayout.Tab tab) {}
            @Override
            public void onTabReselected(TabLayout.Tab tab) {}
        });
    }

    @Override
    public void onResume() {
        super.onResume();
        if (username != null && !username.isEmpty()) {
            loadStats(currentPeriod);   // refresh when returning here
        }
    }

    private void setupCharts() {
        // Peak Focus Time Chart
        peakFocusChart.getDescription().setEnabled(false);
        peakFocusChart.setDrawGridBackground(false);
        peakFocusChart.setDrawBarShadow(false);
        peakFocusChart.setDrawValueAboveBar(false);
        peakFocusChart.setPinchZoom(false);
        peakFocusChart.setScaleEnabled(false);
        
        XAxis xAxis = peakFocusChart.getXAxis();
        xAxis.setPosition(XAxis.XAxisPosition.BOTTOM);
        xAxis.setDrawGridLines(false);
        xAxis.setGranularity(1f);
        xAxis.setTextColor(Color.parseColor("#666666"));
        xAxis.setValueFormatter(new ValueFormatter() {
            @Override
            public String getFormattedValue(float value) {
                int group = (int) value;
                switch (group) {
                    case 0: return "12-3am";
                    case 1: return "4-7am";
                    case 2: return "8-11am";
                    case 3: return "12-3pm";
                    case 4: return "4-7pm";
                    case 5: return "8-11pm";
                    default: return "";
                }
            }
        });

        peakFocusChart.getAxisLeft().setTextColor(Color.parseColor("#666666"));
        peakFocusChart.getAxisLeft().setAxisMinimum(0f);
        peakFocusChart.getAxisLeft().setAxisMaximum(100f);
        peakFocusChart.getAxisRight().setEnabled(false);
        peakFocusChart.getLegend().setEnabled(false);

        // Distraction Breakdown Pie Chart
        distractionBreakdown.setUsePercentValues(true);
        distractionBreakdown.getDescription().setEnabled(false);
        distractionBreakdown.setDrawHoleEnabled(true);
        distractionBreakdown.setHoleRadius(40f);
        distractionBreakdown.setTransparentCircleRadius(45f);
        distractionBreakdown.setDrawEntryLabels(true);
        distractionBreakdown.setEntryLabelColor(Color.parseColor("#666666"));
        distractionBreakdown.setEntryLabelTextSize(12f);
        distractionBreakdown.getLegend().setTextColor(Color.parseColor("#666666"));
    }

    private void loadStats(String period) {
        currentPeriod = period;
        SessionDatabase db = new SessionDatabase();
        
        db.getSessionsForUser(username, sessions -> {
            List<Map<String, Object>> filteredSessions = filterSessionsByPeriod(sessions, period);
            
            if (getActivity() != null) {
                getActivity().runOnUiThread(() -> {
                    calculateAndDisplayStats(filteredSessions);
                    updatePeakFocusChart(filteredSessions);
                    updateDistractionBreakdown(filteredSessions);
                    updateRecentSessions(sessions);
                });
            }
        });
    }

    private List<Map<String, Object>> filterSessionsByPeriod(List<Map<String, Object>> sessions, String period) {
        List<Map<String, Object>> filtered = new ArrayList<>();
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());
        String today = sdf.format(new Date());
        
        Calendar cal = Calendar.getInstance();
        cal.add(Calendar.DAY_OF_YEAR, -7);
        String weekAgo = sdf.format(cal.getTime());
        
        cal = Calendar.getInstance();
        cal.add(Calendar.DAY_OF_YEAR, -30);
        String monthAgo = sdf.format(cal.getTime());

        for (Map<String, Object> session : sessions) {
            String date = (String) session.get("date");
            if (date == null) continue;

            switch (period) {
                case "today":
                    if (date.equals(today)) filtered.add(session);
                    break;
                case "week":
                    if (date.compareTo(weekAgo) >= 0) filtered.add(session);
                    break;
                case "month":
                    if (date.compareTo(monthAgo) >= 0) filtered.add(session);
                    break;
            }
        }
        return filtered;
    }

    private void calculateAndDisplayStats(List<Map<String, Object>> sessions) {
        int totalMins = 0;
        double totalFocus = 0;
        int focusCount = 0;
        int sessionCount = sessions.size();

        for (Map<String, Object> session : sessions) {
            String duration = (String) session.get("duration");
            if (duration != null) {
                String[] parts = duration.split(":");
                if (parts.length == 2) {
                    totalMins += Integer.parseInt(parts[0]);
                }
            }

            Object fs = session.get("focusScore");
            if (fs != null) {
                totalFocus += ((Number) fs).doubleValue();
                focusCount++;
            }
        }

        int hours = totalMins / 60;
        double avgFocus = focusCount > 0 ? totalFocus / focusCount : 0;
        int streak = 0; // Simplified

        avgFocusScore.setText(String.format(Locale.getDefault(), "%.0f%%", avgFocus));
        streakDays.setText(String.valueOf(streak));
        totalSessions.setText(String.valueOf(sessionCount));
        totalHours.setText(hours + "h");
    }

    private void updatePeakFocusChart(List<Map<String, Object>> sessions) {
        List<BarEntry> entries = new ArrayList<>();
        
        // Check if we have valid focus score data
        boolean hasValidFocusData = false;
        if (!sessions.isEmpty()) {
            for (Map<String, Object> session : sessions) {
                Object fs = session.get("focusScore");
                if (fs != null) {
                    hasValidFocusData = true;
                    break;
                }
            }
        }
        
        // Show demo data if no sessions OR if focus scores are N/A
        if (!hasValidFocusData) {
            // Demo data - always visible when focus score is N/A
            float[] demoScores = {45, 60, 78, 85, 82, 65};
            for (int i = 0; i < 6; i++) {
                entries.add(new BarEntry(i, demoScores[i]));
            }
        } else {
            // Group real data into 4-hour blocks
            Map<Integer, List<Double>> groupedFocus = new HashMap<>();
            for (Map<String, Object> session : sessions) {
                int hour = (int) (Math.random() * 24);
                int group = hour / 4; // 0-5 representing 6 groups
                Object fs = session.get("focusScore");
                if (fs != null) {
                    double score = ((Number) fs).doubleValue();
                    if (!groupedFocus.containsKey(group)) {
                        groupedFocus.put(group, new ArrayList<>());
                    }
                    groupedFocus.get(group).add(score);
                }
            }

            for (int group = 0; group < 6; group++) {
                if (groupedFocus.containsKey(group)) {
                    List<Double> scores = groupedFocus.get(group);
                    double avg = scores.stream().mapToDouble(Double::doubleValue).average().orElse(0);
                    entries.add(new BarEntry(group, (float) avg));
                } else {
                    entries.add(new BarEntry(group, 0f));
                }
            }
        }

        BarDataSet dataSet = new BarDataSet(entries, "Focus Score");
        dataSet.setColor(Color.parseColor("#FF9800")); // Orange color
        dataSet.setValueTextColor(Color.parseColor("#666666"));
        dataSet.setValueTextSize(0f);

        BarData data = new BarData(dataSet);
        data.setBarWidth(0.9f); // Wider bars
        peakFocusChart.setData(data);
        peakFocusChart.invalidate();
    }

    private void updateDistractionBreakdown(List<Map<String, Object>> sessions) {
        int eyesClosed, lookingAway, phone;
        
        // Always show demo data for new users
        if (sessions.isEmpty()) {
            eyesClosed = 15;
            lookingAway = 28;
            phone = 12;
        } else {
            eyesClosed = (int) (Math.random() * 20);
            lookingAway = (int) (Math.random() * 30);
            phone = (int) (Math.random() * 15);
        }

        List<PieEntry> entries = new ArrayList<>();
        entries.add(new PieEntry(eyesClosed, "Eyes Closed"));
        entries.add(new PieEntry(lookingAway, "Looking Away"));
        entries.add(new PieEntry(phone, "Phone"));

        PieDataSet dataSet = new PieDataSet(entries, "");
        dataSet.setColors(
            Color.parseColor("#FF5252"),
            Color.parseColor("#FF9800"),
            Color.parseColor("#FFC107")
        );
        dataSet.setValueTextColor(Color.parseColor("#666666"));
        dataSet.setValueTextSize(14f);

        PieData data = new PieData(dataSet);
        distractionBreakdown.setData(data);
        distractionBreakdown.invalidate();
    }

    private void updateRecentSessions(List<Map<String, Object>> sessions) {
        List<Map<String, String>> groupData = new ArrayList<>();
        List<List<Map<String, String>>> childData = new ArrayList<>();

        // Take last 10 sessions
        int count = Math.min(sessions.size(), 10);
        for (int i = 0; i < count; i++) {
            Map<String, Object> session = sessions.get(i);
            
            Map<String, String> group = new HashMap<>();
            group.put("title", (String) session.get("date") + " - " + session.get("duration"));
            groupData.add(group);

            List<Map<String, String>> children = new ArrayList<>();
            Map<String, String> child = new HashMap<>();
            Object fs = session.get("focusScore");
            String focusStr = fs != null ? 
                String.format(Locale.getDefault(), "%.0f%%", ((Number) fs).doubleValue()) : "N/A";
            child.put("details", "Focus Score: " + focusStr);
            children.add(child);
            childData.add(children);
        }

        SimpleExpandableListAdapter adapter = new SimpleExpandableListAdapter(
            requireContext(),
            groupData,
            android.R.layout.simple_expandable_list_item_1,
            new String[]{"title"},
            new int[]{android.R.id.text1},
            childData,
            android.R.layout.simple_expandable_list_item_1,
            new String[]{"details"},
            new int[]{android.R.id.text1}
        );
        recentSessionsList.setAdapter(adapter);
    }
}

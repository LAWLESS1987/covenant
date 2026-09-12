package org.covenant.node;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ResolveInfo;
import android.os.Bundle;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;
import android.widget.Toast;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * "Apps Covenant may use": every launchable app on the phone with a switch,
 * all OFF until the operator turns one on. The list is the green light; the
 * actuator (CovenantActuator) refuses any app that is not on it. Saved in
 * settings.json beside the node's own settings.
 */
public class AppsActivity extends Activity {
    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        Settings s = Settings.load(this);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("Apps Covenant may use");
        title.setTextSize(20);
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        col.addView(title);

        TextView about = new TextView(this);
        about.setText("A switch here is the green light. Off means Covenant will never touch that app. "
                + "Acting also needs the actuator, which only you can enable, in Android's Accessibility settings. "
                + "Every action and every refusal is written to the app's actions.log.");
        about.setPadding(0, pad / 2, 0, pad / 2);
        col.addView(about);

        Button enable = new Button(this);
        enable.setText(CovenantActuator.isConnected() ? "Actuator: enabled (open Android settings)" : "Actuator: OFF -- enable it in Android settings");
        enable.setOnClickListener(v -> startActivity(new Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS)));
        col.addView(enable);

        PackageManager pm = getPackageManager();
        Intent main = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER);
        List<ResolveInfo> apps = new ArrayList<>(pm.queryIntentActivities(main, 0));
        Collections.sort(apps, (x, y) -> String.valueOf(x.loadLabel(pm)).compareToIgnoreCase(String.valueOf(y.loadLabel(pm))));
        int n = 0;
        for (ResolveInfo ri : apps) {
            final String pkg = ri.activityInfo.packageName;
            if (pkg.equals(getPackageName())) continue;
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            row.setGravity(android.view.Gravity.CENTER_VERTICAL);
            row.setPadding(0, pad / 2, 0, pad / 2);
            ImageView icon = new ImageView(this);
            icon.setImageDrawable(ri.loadIcon(pm));
            int sz = (int) (36 * getResources().getDisplayMetrics().density);
            row.addView(icon, new LinearLayout.LayoutParams(sz, sz));
            TextView name = new TextView(this);
            name.setText(ri.loadLabel(pm) + "\n" + pkg);
            name.setPadding(pad / 2, 0, pad / 2, 0);
            row.addView(name, new LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f));
            Switch sw = new Switch(this);
            sw.setChecked(s.allowedApps.contains(pkg));
            sw.setOnCheckedChangeListener((btn, on) -> {
                Settings cur = Settings.load(this);
                if (on) cur.allowedApps.add(pkg); else cur.allowedApps.remove(pkg);
                try {
                    Settings.save(this, cur);
                    CovenantActuator.log(this, pkg, on ? "green-lit by the operator" : "green light withdrawn by the operator");
                } catch (Exception e) {
                    Toast.makeText(this, "could not save: " + e, Toast.LENGTH_LONG).show();
                }
            });
            row.addView(sw);
            col.addView(row);
            n++;
        }
        if (n == 0) {
            TextView none = new TextView(this);
            none.setText("No launchable apps visible (the manifest's <queries> lists the launcher intent; if this is empty, Android hid them).");
            col.addView(none);
        }
        ScrollView sv = new ScrollView(this);
        sv.addView(col);
        setContentView(sv);
    }
}

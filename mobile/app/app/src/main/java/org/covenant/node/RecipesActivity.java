package org.covenant.node;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONObject;

import java.util.ArrayList;
import java.util.List;

/**
 * "Recipes": what the preliminary brain knows. Record a new one (show it once
 * in a green-lit app), run one (its slot text goes through the gate first),
 * read what each has learned, delete what it learned wrong. Everything on
 * this phone; see Recipe.java for what learning means here.
 */
public class RecipesActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private LinearLayout col;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        ScrollView sv = new ScrollView(this);
        col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (16 * getResources().getDisplayMetrics().density);
        col.setPadding(pad, pad, pad, pad);
        col.setBackgroundColor(getColor(R.color.bg));
        sv.setBackgroundColor(getColor(R.color.bg));
        sv.addView(col);
        setContentView(sv);
    }

    @Override protected void onResume() { super.onResume(); render(); }

    private void render() {
        col.removeAllViews();
        TextView title = new TextView(this);
        title.setText("Recipes -- what the brain has learned");
        title.setTextSize(20); title.setTypeface(null, android.graphics.Typeface.BOLD);
        col.addView(title);
        TextView about = new TextView(this);
        about.setText("A recipe is something you did once in a green-lit app while the actuator watched. "
                + "Replaying it, the brain tries the locator it trusts most for each step and learns which one worked. "
                + "Text you typed is a slot: it asks for it, and the gate judges it, before it goes in. Nothing leaves the phone.");
        col.addView(about);

        if (CovenantActuator.isRecording()) {
            Button stop = new Button(this);
            stop.setText("STOP recording and keep it");
            stop.setOnClickListener(v -> {
                Recipe r = CovenantActuator.stopRecording();
                if (r == null) return;
                if (r.steps.isEmpty()) { Toast.makeText(this, "nothing was recorded", Toast.LENGTH_LONG).show(); render(); return; }
                try { r.save(this); Toast.makeText(this, "kept: " + r.steps.size() + " step(s)", Toast.LENGTH_SHORT).show(); }
                catch (Exception e) { Toast.makeText(this, "could not keep it: " + e, Toast.LENGTH_LONG).show(); }
                render();
            });
            col.addView(stop);
        } else {
            Button rec = new Button(this);
            rec.setText("Record a new recipe...");
            rec.setOnClickListener(v -> recordNew());
            col.addView(rec);
        }

        List<Recipe> all = Recipe.all(this);
        if (all.isEmpty()) {
            TextView none = new TextView(this);
            none.setText("\nNo recipes yet.");
            col.addView(none);
        }
        for (Recipe r : all) {
            TextView t = new TextView(this);
            StringBuilder sb = new StringBuilder();
            sb.append("\n").append(r.name).append("  (").append(r.pkg).append(")\n");
            for (int i = 0; i < r.steps.size(); i++) {
                Recipe.Step s = r.steps.get(i);
                sb.append("  ").append(i + 1).append(". ").append(s.describe())
                  .append("   trusts: ").append(String.join(" > ", s.order())).append("\n");
            }
            if (!r.runs.isEmpty()) sb.append("  last run: ").append(r.runs.get(r.runs.size() - 1)).append("\n");
            if (!r.lastAnswer.isEmpty()) sb.append("  last answer:\n").append(r.lastAnswer.length() > 700 ? r.lastAnswer.substring(0, 700) + "..." : r.lastAnswer).append("\n");
            t.setText(sb.toString());
            t.setTypeface(android.graphics.Typeface.MONOSPACE);
            t.setTextSize(12);
            col.addView(t);
            LinearLayout row = new LinearLayout(this);
            row.setOrientation(LinearLayout.HORIZONTAL);
            Button run = new Button(this); run.setText("Run"); run.setOnClickListener(v -> run(r)); row.addView(run);
            if (!r.lastAnswer.isEmpty()) {
                Button share = new Button(this); share.setText("Share answer");
                share.setOnClickListener(v -> startActivity(Intent.createChooser(new Intent(Intent.ACTION_SEND).setType("text/plain")
                        .putExtra(Intent.EXTRA_TEXT, r.lastAnswer), "Share from Covenant")));
                row.addView(share);
            }
            Button del = new Button(this); del.setText("Delete");
            del.setOnClickListener(v -> new AlertDialog.Builder(this).setTitle("Delete '" + r.name + "'?")
                    .setPositiveButton("Delete", (d, w) -> { r.file(this).delete(); CovenantActuator.log(this, r.pkg, "recipe '" + r.name + "' deleted by the operator"); render(); })
                    .setNegativeButton("Keep", null).show());
            row.addView(del);
            col.addView(row);
        }
        skin(col);
    }

    private void recordNew() {
        if (!CovenantActuator.isConnected()) {
            Toast.makeText(this, "the actuator is off: enable 'Covenant actuator' in Android's Accessibility settings", Toast.LENGTH_LONG).show();
            startActivity(new Intent(android.provider.Settings.ACTION_ACCESSIBILITY_SETTINGS));
            return;
        }
        final List<String> pkgs = new ArrayList<>(Settings.load(this).allowedApps);
        if (pkgs.isEmpty()) { Toast.makeText(this, "no app is green-lit yet", Toast.LENGTH_LONG).show(); startActivity(new Intent(this, AppsActivity.class)); return; }
        final String[] labels = new String[pkgs.size()];
        for (int i = 0; i < pkgs.size(); i++) {
            try { labels[i] = getPackageManager().getApplicationLabel(getPackageManager().getApplicationInfo(pkgs.get(i), 0)) + "  (" + pkgs.get(i) + ")"; }
            catch (Exception e) { labels[i] = pkgs.get(i); }
        }
        new AlertDialog.Builder(this).setTitle("Show it in which app?").setItems(labels, (d, which) -> {
            EditText name = new EditText(this);
            name.setHint("name, e.g. post an update");
            new AlertDialog.Builder(this).setTitle("Name the recipe").setView(name)
                    .setPositiveButton("Start recording", (d2, w) -> {
                        String nm = name.getText().toString().trim();
                        if (nm.isEmpty()) { Toast.makeText(this, "it needs a name", Toast.LENGTH_SHORT).show(); return; }
                        Recipe r = new Recipe(); r.name = nm; r.pkg = pkgs.get(which);
                        if (!CovenantActuator.startRecording(r)) { Toast.makeText(this, "busy replaying; try again in a moment", Toast.LENGTH_SHORT).show(); return; }
                        CovenantActuator.log(this, r.pkg, "recording '" + nm + "' started by the operator");
                        Toast.makeText(this, "do it once in the app, then come back here and tap STOP", Toast.LENGTH_LONG).show();
                        Intent launch = getPackageManager().getLaunchIntentForPackage(r.pkg);
                        if (launch != null) startActivity(launch);
                    })
                    .setNegativeButton("Cancel", null).show();
        }).show();
    }

    private void run(Recipe r) {
        if (!CovenantActuator.isConnected()) { Toast.makeText(this, "the actuator is off", Toast.LENGTH_LONG).show(); return; }
        if (!r.hasSlot()) { go(r, ""); return; }
        EditText box = new EditText(this);
        box.setHint("the text this run should type"); box.setMinLines(2);
        new AlertDialog.Builder(this).setTitle("Run '" + r.name + "'").setView(box)
                .setPositiveButton("Judge, then run", (d, w) -> judgeThen(r, box.getText().toString()))
                .setNegativeButton("Cancel", null).show();
    }

    /** The node's own gate first: a REFUSED text never goes in; a hold that alleges nothing is logged and passes (A98). */
    private void judgeThen(Recipe r, String text) {
        if (text.trim().isEmpty()) { Toast.makeText(this, "nothing to type", Toast.LENGTH_SHORT).show(); return; }
        AlertDialog wait = new AlertDialog.Builder(this).setTitle("Judging first...").setCancelable(false).create();
        wait.show();
        new Thread(() -> {
            String verdict = "REFUSED", why = "";
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
                PyObject o = Python.getInstance().getModule("entry").callAttr("judge_text",
                        getFilesDir().getAbsolutePath(), getApplicationInfo().sourceDir, text);
                JSONObject j = new JSONObject(o.toString());
                verdict = j.optBoolean("admitted") ? "ADMITTED" : (j.optBoolean("alleges_nothing") ? "HELD" : "REFUSED");
                why = j.optString("message");
            } catch (Throwable t) { why = "could not judge: " + t; }
            final String v = verdict, wy = why;
            handler.post(() -> {
                wait.dismiss();
                CovenantActuator.log(this, r.pkg, "recipe '" + r.name + "' slot text " + text.length() + " chars; gate said " + v + (wy.isEmpty() ? "" : " -- " + wy));
                if (v.equals("REFUSED")) { new AlertDialog.Builder(this).setTitle("Refused by the gate").setMessage(wy).setPositiveButton("Close", null).show(); return; }
                go(r, text);
            });
        }, "covenant-judge").start();
    }

    private void go(Recipe r, String slot) {
        if (!CovenantActuator.startPlaying(r, slot)) { Toast.makeText(this, "busy; try again in a moment", Toast.LENGTH_SHORT).show(); return; }
        CovenantActuator.log(this, r.pkg, "recipe '" + r.name + "' run started by the operator");
        Intent launch = getPackageManager().getLaunchIntentForPackage(r.pkg);
        if (launch == null) { Toast.makeText(this, "cannot open " + r.pkg, Toast.LENGTH_LONG).show(); return; }
        Toast.makeText(this, "replaying '" + r.name + "'; come back here to see the result", Toast.LENGTH_LONG).show();
        startActivity(launch);
    }

    /** The main screen's look, applied to a screen built in code: paper, ink, the rounded secondary button. */
    private void skin(android.view.View v) {
        if (v instanceof Button) {
            Button b = (Button) v;
            b.setBackgroundResource(R.drawable.btn_secondary);
            b.setTextColor(getColor(R.color.accent));
            b.setAllCaps(false);
            b.setStateListAnimator(null);
            if (b.getLayoutParams() instanceof LinearLayout.LayoutParams) {
                LinearLayout.LayoutParams lp = (LinearLayout.LayoutParams) b.getLayoutParams();
                lp.topMargin = (int) (6 * getResources().getDisplayMetrics().density);
                b.setLayoutParams(lp);
            }
        } else if (v instanceof TextView) {
            ((TextView) v).setTextColor(getColor(R.color.ink));
        }
        if (v instanceof android.view.ViewGroup) {
            android.view.ViewGroup g = (android.view.ViewGroup) v;
            for (int i = 0; i < g.getChildCount(); i++) skin(g.getChildAt(i));
        }
    }
}

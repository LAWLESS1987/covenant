package org.covenant.node;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.os.PowerManager;
import android.text.InputType;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * The minimum UI, built in code, ugly on purpose: Start/Stop, one status line
 * from /health, the PC_PEER and port fields, "Start at boot", Save, Open
 * dashboard, the battery exemption, the last log lines and the last exit reason.
 *
 * SHARE IN / SHARE OUT. Any app's Share sheet can hand this Activity a text
 * (ACTION_SEND text/plain); it is judged IN THIS PROCESS by the same gate the
 * node uses -- entry.judge_text builds the node's own quorum and sentinel --
 * and the verdict is shown with a Share button, so it can go back out to any
 * app. Nothing is sent anywhere, no HTTP endpoint is added to the node, and
 * the node does not need to be running for a share to be judged.
 */
public class MainActivity extends Activity {
    private TextView status, log;
    private EditText pcPeer, port;
    private CheckBox autostart;
    private final Handler handler = new Handler(Looper.getMainLooper());
    private boolean polling = false;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (12 * getResources().getDisplayMetrics().density);
        col.setPadding(pad, pad, pad, pad);

        status = mono(col);
        status.setText("checking...");

        pcPeer = new EditText(this);
        pcPeer.setHint("PC peer host:port, e.g. 10.0.0.174:5001 (PC API port + 1); over the USB cable 127.0.0.1:15001; blank = run alone");
        pcPeer.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        col.addView(pcPeer);

        port = new EditText(this);
        port.setHint("API port (default 5000); the node also binds +1 and +11");
        port.setInputType(InputType.TYPE_CLASS_NUMBER);
        col.addView(port);

        autostart = new CheckBox(this);
        autostart.setText("Start at boot");
        col.addView(autostart);

        button(col, "Save settings (takes effect on next Start)", v -> save(true));
        button(col, "Start", v -> {
            if (!save(false)) return;
            new File(getFilesDir(), "last_exit.txt").delete();
            startForegroundService(new Intent(this, NodeService.class));
        });
        button(col, "Stop", v -> stopService(new Intent(this, NodeService.class)));
        button(col, "Open dashboard", v -> startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse("http://127.0.0.1:" + currentPort() + "/"))));
        button(col, "Share status", v -> shareText(status.getText() + "\nhttp://127.0.0.1:" + currentPort() + "/health"));
        button(col, "Judge a text...", v -> askForText());
        button(col, "Battery: allow unrestricted", v -> {
            PowerManager pm = getSystemService(PowerManager.class);
            if (pm.isIgnoringBatteryOptimizations(getPackageName())) {
                Toast.makeText(this, "already unrestricted", Toast.LENGTH_SHORT).show();
            } else {
                startActivity(new Intent(android.provider.Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS, Uri.parse("package:" + getPackageName())));
            }
        });

        TextView hint = new TextView(this);
        hint.setText("Samsung: Settings > Apps > Covenant Node > Battery > Unrestricted, and Battery > Background usage limits > Never sleeping apps. "
                + "Add this phone's IP:5001 to the PC node's --peers, or use mobile/usb_link.py over a cable. "
                + "Share any text to this app from another app to judge it.");
        col.addView(hint);

        log = mono(col);

        ScrollView sv = new ScrollView(this);
        sv.addView(col);
        setContentView(sv);

        Settings s = Settings.load(this);
        pcPeer.setText(s.pcPeer);
        port.setText(String.valueOf(s.port));
        autostart.setChecked(s.autostart);

        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, 1);   // the service runs either way; this makes its notification visible
        }
        handleShare(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        handleShare(intent);
    }

    // ------------------------------------------------------------- share in / out

    private void handleShare(Intent intent) {
        if (intent == null || !Intent.ACTION_SEND.equals(intent.getAction())) return;
        String text = intent.getStringExtra(Intent.EXTRA_TEXT);
        if (text == null || text.trim().isEmpty()) return;
        judge(text);
    }

    private void askForText() {
        EditText box = new EditText(this);
        box.setHint("text to judge");
        box.setMinLines(3);
        new AlertDialog.Builder(this).setTitle("Judge a text").setView(box)
                .setPositiveButton("Judge", (d, w) -> judge(box.getText().toString()))
                .setNegativeButton("Cancel", null).show();
    }

    /** Judge in this process with the node's own gate; show the verdict; offer to share it. */
    private void judge(String text) {
        AlertDialog wait = new AlertDialog.Builder(this).setTitle("Judging...").setMessage("first time takes a few seconds while the judges load").setCancelable(false).create();
        wait.show();
        new Thread(() -> {
            String verdict;
            try {
                if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
                PyObject r = Python.getInstance().getModule("entry").callAttr("judge_text",
                        getFilesDir().getAbsolutePath(), getApplicationInfo().sourceDir, text);
                JSONObject j = new JSONObject(r.toString());
                verdict = (j.optBoolean("admitted") ? "ADMITTED" : (j.optBoolean("alleges_nothing") ? "HELD (nothing alleged)" : "REFUSED"))
                        + "\n\n" + j.optString("message")
                        + "\n\njudge: " + j.optString("judge")
                        + "\n\ntext:\n" + (text.length() > 600 ? text.substring(0, 600) + "..." : text);
            } catch (Throwable t) {
                verdict = "could not judge: " + t;
            }
            final String v = verdict;
            handler.post(() -> {
                wait.dismiss();
                new AlertDialog.Builder(this).setTitle("Covenant verdict").setMessage(v)
                        .setPositiveButton("Share verdict", (d, w) -> shareText(v))
                        .setNegativeButton("Close", null).show();
            });
        }, "covenant-judge").start();
    }

    private void shareText(String text) {
        Intent send = new Intent(Intent.ACTION_SEND).setType("text/plain").putExtra(Intent.EXTRA_TEXT, text);
        startActivity(Intent.createChooser(send, "Share from Covenant"));
    }

    // ------------------------------------------------------------- settings

    private int currentPort() {
        try { return Integer.parseInt(port.getText().toString().trim()); } catch (Exception e) { return 5000; }
    }

    private boolean save(boolean toast) {
        Settings s = new Settings();
        s.pcPeer = pcPeer.getText().toString().trim();
        s.nodeId = "phone";
        s.autostart = autostart.isChecked();
        try { s.port = Integer.parseInt(port.getText().toString().trim()); } catch (Exception e) { s.port = -1; }
        if (!Settings.validPeer(s.pcPeer)) { status.setText("PC peer must be host:port (one colon, port 1-65535) or blank"); return false; }
        if (!Settings.validPort(s.port)) { status.setText("port must be 1024-65000 (the node also binds +1 and +11)"); return false; }
        try {
            Settings.save(this, s);
        } catch (Exception e) {
            status.setText("could not save settings: " + e);
            return false;
        }
        if (toast) Toast.makeText(this, "saved; Stop then Start to apply", Toast.LENGTH_SHORT).show();
        return true;
    }

    // ------------------------------------------------------------- status poll

    @Override protected void onResume() { super.onResume(); polling = true; handler.post(this::poll); }
    @Override protected void onPause() { super.onPause(); polling = false; }

    private void poll() {
        if (!polling) return;
        final int p = currentPort();
        new Thread(() -> {
            String line;
            try {
                HttpURLConnection c = (HttpURLConnection) new URL("http://127.0.0.1:" + p + "/health").openConnection();
                c.setConnectTimeout(2000); c.setReadTimeout(2000);
                StringBuilder sb = new StringBuilder();
                try (BufferedReader r = new BufferedReader(new InputStreamReader(c.getInputStream(), StandardCharsets.UTF_8))) {
                    String s; while ((s = r.readLine()) != null) sb.append(s);
                }
                JSONObject h = new JSONObject(sb.toString());   // ANY HTTP answer = UP; `degraded` is true on every keyless phone and is ignored
                String genesis = h.optString("genesis", "");
                boolean own = h.optBoolean("own_genesis", false);
                line = "UP  node=" + h.optString("node_id") + "  height=" + h.opt("chain_height") + "  peers=" + h.opt("peers") + "  pending=" + h.opt("pending_transactions")
                        + "\ngenesis=" + (genesis.length() > 12 ? genesis.substring(0, 12) : genesis) + "  own_genesis=" + own
                        + (own ? "\n!! own_genesis=true: this node cannot converge with peers" : "")
                        + "\njudge=" + h.optString("judge") + "  wsgi=" + h.optString("wsgi") + "  version=" + h.optString("version")
                        + "\nchecked " + new SimpleDateFormat("HH:mm:ss", Locale.US).format(new Date());
            } catch (Exception e) {
                line = "DOWN (" + e.getClass().getSimpleName() + ")";
                File exit = new File(getFilesDir(), "last_exit.txt");
                if (exit.exists()) line += "\nlast exit:\n" + tail(exit, 12);
            }
            final String l = line;
            final String tailLog = tail(new File(getFilesDir(), "node.log"), 20);
            handler.post(() -> { status.setText(l); log.setText(tailLog); if (polling) handler.postDelayed(this::poll, 3000); });
        }, "covenant-poll").start();
    }

    private static String tail(File f, int n) {
        try (BufferedReader r = new BufferedReader(new FileReader(f))) {
            List<String> lines = new ArrayList<>();
            String s; while ((s = r.readLine()) != null) { lines.add(s); if (lines.size() > n) lines.remove(0); }
            return String.join("\n", lines);
        } catch (Exception e) {
            return "";
        }
    }

    // ------------------------------------------------------------- widgets

    private TextView mono(LinearLayout col) {
        TextView t = new TextView(this);
        t.setTypeface(Typeface.MONOSPACE);
        t.setTextIsSelectable(true);
        col.addView(t);
        return t;
    }

    private void button(LinearLayout col, String label, android.view.View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(label);
        b.setOnClickListener(l);
        col.addView(b);
    }
}

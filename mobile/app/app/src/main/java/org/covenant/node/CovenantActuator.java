package org.covenant.node;

import android.accessibilityservice.AccessibilityService;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * PHASE 1 of "use my other apps" (the operator's decision, 2026-09-12): the
 * actuator. An Android Accessibility service that the operator enables HIMSELF
 * in Android settings (there is no way to enable one from code), which then
 * acts only inside apps he has green-lit in this app (Settings.allowedApps),
 * only on a job placed from THIS phone (MainActivity's "Use an app..."), and
 * writes every action -- and every refusal -- to files/actions.log.
 *
 * What it can do: put a text into the editable field of a green-lit app's
 * current screen, and press its Send/Post/Submit button. What it cannot do:
 * gestures (canPerformGestures is not requested), anything in an app that is
 * not green-lit, anything without a job, anything from the PC. Remote driving
 * waits for a signing key only the operator holds: this APK is signed with a
 * public debug key, and an accessibility grant on an app anyone can install
 * over would hand the phone to whoever did.
 */
public class CovenantActuator extends AccessibilityService {
    static final class Job {
        final String pkg, text;
        final boolean send;
        final long created = System.currentTimeMillis();
        Job(String pkg, String text, boolean send) { this.pkg = pkg; this.text = text; this.send = send; }
    }

    private static volatile Job pending;
    private static volatile boolean connected;
    private static final String[] SEND_WORDS = {"send", "post", "submit", "share", "reply", "tweet", "done"};

    static boolean isConnected() { return connected; }
    static void submit(Job j) { pending = j; }

    @Override
    public void onServiceConnected() {
        connected = true;
        log(this, "-", "actuator enabled by the operator in Android settings");
    }

    @Override
    public boolean onUnbind(Intent intent) {
        connected = false;
        log(this, "-", "actuator disabled");
        return super.onUnbind(intent);
    }

    @Override public void onInterrupt() { }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent e) {
        Job j = pending;
        if (j == null || e == null) return;
        if (System.currentTimeMillis() - j.created > 60_000) {
            pending = null;
            log(this, j.pkg, "job expired: the app's screen did not appear within 60 s");
            return;
        }
        CharSequence p = e.getPackageName();
        if (p == null || !p.toString().equals(j.pkg)) return;              // some other app's event: not ours to touch
        if (!Settings.load(this).allowedApps.contains(j.pkg)) {
            pending = null;
            log(this, j.pkg, "REFUSED: not green-lit in Covenant");
            return;
        }
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;
        AccessibilityNodeInfo field = findEditable(root);
        if (field == null) return;                                        // no field yet; the next event may bring one
        pending = null;
        Bundle args = new Bundle();
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, j.text);
        field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
        boolean ok = field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
        log(this, j.pkg, "put " + j.text.length() + " chars into the field: " + (ok ? "ok" : "FAILED"));
        if (!j.send || !ok) return;
        AccessibilityNodeInfo btn = findSend(getRootInActiveWindow());
        if (btn == null) {
            log(this, j.pkg, "no Send/Post/Submit button found; the text is in the field, nothing was sent");
            return;
        }
        boolean sent = btn.performAction(AccessibilityNodeInfo.ACTION_CLICK);
        log(this, j.pkg, "pressed '" + label(btn) + "': " + (sent ? "ok" : "FAILED"));
    }

    private static AccessibilityNodeInfo findEditable(AccessibilityNodeInfo n) {
        if (n == null) return null;
        if (n.isEditable() && n.isVisibleToUser() && n.isFocused()) return n;
        AccessibilityNodeInfo any = null;
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = findEditable(n.getChild(i));
            if (r != null) {
                if (r.isFocused()) return r;
                if (any == null) any = r;
            }
        }
        if (any != null) return any;
        return (n.isEditable() && n.isVisibleToUser()) ? n : null;
    }

    private static AccessibilityNodeInfo findSend(AccessibilityNodeInfo n) {
        if (n == null) return null;
        if (n.isClickable() && n.isVisibleToUser()) {
            String l = label(n).toLowerCase(Locale.US).trim();
            for (String w : SEND_WORDS) if (l.equals(w) || l.startsWith(w + " ")) return n;
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = findSend(n.getChild(i));
            if (r != null) return r;
        }
        return null;
    }

    private static String label(AccessibilityNodeInfo n) {
        CharSequence t = n.getText();
        if (t == null || t.length() == 0) t = n.getContentDescription();
        return t == null ? "" : t.toString();
    }

    /** files/actions.log: one line per action or refusal, kept, never rotated by this class. */
    static void log(Context c, String pkg, String what) {
        String line = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date()) + "  " + pkg + "  " + what;
        Log.i("covenant", "actuator: " + line);
        try (OutputStreamWriter w = new OutputStreamWriter(new FileOutputStream(new File(c.getFilesDir(), "actions.log"), true), StandardCharsets.UTF_8)) {
            w.write(line + "\n");
        } catch (Exception ignored) {
            // the log is a record, not a gate; a full disk must not stop the app
        }
    }
}

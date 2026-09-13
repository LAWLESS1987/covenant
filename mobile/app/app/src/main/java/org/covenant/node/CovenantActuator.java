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
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.Locale;

/**
 * The actuator (phase 1, 2026-09-12) and the preliminary brain's hands and
 * eyes (phase 2, the same day). An Android Accessibility service the operator
 * enables HIMSELF in Android settings (no code can), which acts only inside
 * apps he has green-lit (Settings.allowedApps), only on a job placed from THIS
 * phone, and writes every action and refusal to files/actions.log.
 *
 * Three modes, one at a time:
 *   JOB        put a text into the green-lit app's field, press Send (phase 1).
 *   RECORDING  watch the owner use a green-lit app and keep what he did as a
 *              Recipe: each tap's target, each text, each scroll. Only that
 *              app's events are looked at; the recording ends when he returns
 *              to Covenant and taps Stop. Nothing is judged or sent.
 *   PLAYING    replay a Recipe: find each step's target by the locator the
 *              recipe trusts most, act, learn which locator worked.
 * No gestures are requested. Nothing leaves the phone. Remote driving waits
 * for a signing key only the operator holds (this APK's key is public).
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

    // ---- recording
    private static volatile Recipe recording;
    private static volatile String lastTypedId = "";
    // ---- playing
    private static volatile Recipe playing;
    private static volatile String slotText = "";
    private static volatile int stepAt = 0;
    private static volatile long stepSince = 0;
    private static volatile long playStarted = 0;
    private static volatile String playResult = "";

    static boolean isConnected() { return connected; }
    static void submit(Job j) { pending = j; }

    static boolean startRecording(Recipe r) { if (playing != null) return false; recording = r; lastTypedId = ""; return true; }
    static Recipe stopRecording() { Recipe r = recording; recording = null; return r; }
    static boolean isRecording() { return recording != null; }
    static boolean startPlaying(Recipe r, String slot) {
        if (recording != null || playing != null) return false;
        playing = r; slotText = slot == null ? "" : slot; stepAt = 0; stepSince = System.currentTimeMillis(); playStarted = stepSince; playResult = "";
        return true;
    }
    static boolean isPlaying() { return playing != null; }
    static String lastPlayResult() { return playResult; }

    @Override
    public void onServiceConnected() {
        connected = true;
        log(this, "-", "actuator enabled by the operator in Android settings");
    }

    @Override
    public boolean onUnbind(Intent intent) {
        connected = false;
        recording = null; playing = null;
        log(this, "-", "actuator disabled");
        return super.onUnbind(intent);
    }

    @Override public void onInterrupt() { }

    @Override
    public void onAccessibilityEvent(AccessibilityEvent e) {
        if (e == null) return;
        CharSequence p = e.getPackageName();
        String pkg = p == null ? "" : p.toString();
        if (recording != null) { record(e, pkg); return; }
        if (playing != null) { play(e, pkg); return; }
        Job j = pending;
        if (j == null) return;
        if (System.currentTimeMillis() - j.created > 60_000) {
            pending = null;
            log(this, j.pkg, "job expired: the app's screen did not appear within 60 s");
            return;
        }
        if (!pkg.equals(j.pkg)) return;                                   // some other app's event: not ours to touch
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
        boolean ok = setText(field, j.text);
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

    // ------------------------------------------------------------- recording

    private void record(AccessibilityEvent e, String pkg) {
        Recipe r = recording;
        if (r == null || !pkg.equals(r.pkg)) return;                    // only the app being demonstrated
        int t = e.getEventType();
        AccessibilityNodeInfo src = e.getSource();
        if (t == AccessibilityEvent.TYPE_VIEW_CLICKED && src != null) {
            Recipe.Step s = describe(src, "click");
            r.steps.add(s);
            log(this, pkg, "recorded: " + s.describe());
        } else if (t == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED && src != null) {
            String now = e.getText() == null || e.getText().isEmpty() ? "" : String.valueOf(e.getText().get(0));
            Recipe.Step s = describe(src, "type");
            String key = s.id + "|" + s.cls + "|" + s.ordinal;
            if (key.equals(lastTypedId) && !r.steps.isEmpty() && r.steps.get(r.steps.size() - 1).kind.equals("type")) {
                r.steps.get(r.steps.size() - 1).text = now;               // keystrokes collapse into one step
            } else {
                s.text = now; s.slot = true;                                // typed text is a slot: asked for at run time
                r.steps.add(s); lastTypedId = key;
                log(this, pkg, "recorded: typing into " + s.describe());
            }
        } else if (t == AccessibilityEvent.TYPE_VIEW_SCROLLED && src != null) {
            Recipe.Step s = describe(src, "scroll");
            if (r.steps.isEmpty() || !r.steps.get(r.steps.size() - 1).kind.equals("scroll")) { r.steps.add(s); log(this, pkg, "recorded: scroll"); }
        }
    }

    private Recipe.Step describe(AccessibilityNodeInfo n, String kind) {
        Recipe.Step s = new Recipe.Step();
        s.kind = kind;
        s.id = n.getViewIdResourceName() == null ? "" : n.getViewIdResourceName();
        s.text = kind.equals("type") ? "" : (n.getText() == null ? "" : n.getText().toString());
        s.desc = n.getContentDescription() == null ? "" : n.getContentDescription().toString();
        s.cls = n.getClassName() == null ? "" : n.getClassName().toString();
        s.ordinal = ordinalOf(getRootInActiveWindow(), n, s.cls);
        return s;
    }

    // ------------------------------------------------------------- playing

    private void play(AccessibilityEvent e, String pkg) {
        Recipe r = playing;
        if (r == null) return;
        if (System.currentTimeMillis() - playStarted > 120_000) { finish(r, "gave up: 120 s passed", false); return; }
        if (!pkg.equals(r.pkg)) return;
        if (!Settings.load(this).allowedApps.contains(r.pkg)) { finish(r, "REFUSED: not green-lit in Covenant", false); return; }
        if (stepAt >= r.steps.size()) { finish(r, "done: " + r.steps.size() + " step(s)", true); return; }
        if (System.currentTimeMillis() - stepSince < 700) return;         // let the screen settle between steps
        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) return;
        Recipe.Step s = r.steps.get(stepAt);
        if (System.currentTimeMillis() - stepSince > 20_000) { finish(r, "step " + (stepAt + 1) + " (" + s.describe() + ") never appeared", false); return; }
        for (String loc : s.order()) {
            AccessibilityNodeInfo n = locate(root, s, loc);
            if (n == null) { s.learn(loc, false); continue; }
            boolean ok;
            if (s.kind.equals("type")) ok = setText(n, s.slot ? slotText : s.text);
            else if (s.kind.equals("scroll")) ok = n.performAction(AccessibilityNodeInfo.ACTION_SCROLL_FORWARD);
            else ok = n.performAction(AccessibilityNodeInfo.ACTION_CLICK) || clickUp(n);
            s.learn(loc, ok);
            log(this, r.pkg, "step " + (stepAt + 1) + " " + s.describe() + " by " + loc + ": " + (ok ? "ok" : "FAILED"));
            if (ok) { stepAt++; stepSince = System.currentTimeMillis(); return; }
        }
        // nothing found on this screen yet: wait for the next event (the window may still be loading)
    }

    private void finish(Recipe r, String why, boolean ok) {
        playing = null;
        playResult = (ok ? "ok: " : "FAILED: ") + why;
        if (ok) {
            // READ BACK (2026-09-12: "have access to the other ai apps on my phone"):
            // what the green-lit app shows when the recipe is done -- an AI app's
            // answer, a confirmation -- is kept on this phone as the run's answer.
            // It is read once, here, and goes nowhere unless the owner shares it.
            StringBuilder sb = new StringBuilder();
            harvest(getRootInActiveWindow(), sb, 0);
            r.lastAnswer = sb.length() > 6000 ? sb.substring(0, 6000) + "\n..." : sb.toString();
        }
        r.runs.add(new SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).format(new Date()) + " " + playResult
                + " (" + (System.currentTimeMillis() - playStarted) / 1000 + " s)");
        try { r.save(this); } catch (Exception ex) { log(this, r.pkg, "could not save what was learned: " + ex); }
        log(this, r.pkg, "recipe '" + r.name + "' " + playResult);
    }

    private AccessibilityNodeInfo locate(AccessibilityNodeInfo root, Recipe.Step s, String loc) {
        if (loc.equals("id")) {
            List<AccessibilityNodeInfo> l = root.findAccessibilityNodeInfosByViewId(s.id);
            return l == null || l.isEmpty() ? null : l.get(0);
        }
        if (loc.equals("text")) {
            List<AccessibilityNodeInfo> l = root.findAccessibilityNodeInfosByText(s.text);
            if (l != null) for (AccessibilityNodeInfo n : l) if (n.isVisibleToUser()) return n;
            return null;
        }
        if (loc.equals("desc")) return findByDesc(root, s.desc);
        return nthOfClass(root, s.cls, s.ordinal, new int[]{0});
    }

    // ------------------------------------------------------------- node helpers

    private static void harvest(AccessibilityNodeInfo n, StringBuilder sb, int depth) {
        if (n == null || depth > 40 || sb.length() > 6000) return;
        if (n.isVisibleToUser()) {
            CharSequence t = n.getText();
            if (t != null && t.length() > 0 && !n.isEditable()) sb.append(t).append('\n');
        }
        for (int i = 0; i < n.getChildCount(); i++) harvest(n.getChild(i), sb, depth + 1);
    }

    private static boolean setText(AccessibilityNodeInfo field, String text) {
        Bundle args = new Bundle();
        args.putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text);
        field.performAction(AccessibilityNodeInfo.ACTION_FOCUS);
        return field.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args);
    }

    private static boolean clickUp(AccessibilityNodeInfo n) {
        AccessibilityNodeInfo p = n.getParent();
        for (int i = 0; p != null && i < 4; i++, p = p.getParent())
            if (p.isClickable() && p.performAction(AccessibilityNodeInfo.ACTION_CLICK)) return true;
        return false;
    }

    private static AccessibilityNodeInfo findByDesc(AccessibilityNodeInfo n, String desc) {
        if (n == null) return null;
        if (n.getContentDescription() != null && desc.equals(n.getContentDescription().toString()) && n.isVisibleToUser()) return n;
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = findByDesc(n.getChild(i), desc);
            if (r != null) return r;
        }
        return null;
    }

    private static AccessibilityNodeInfo nthOfClass(AccessibilityNodeInfo n, String cls, int want, int[] seen) {
        if (n == null) return null;
        if (n.getClassName() != null && cls.equals(n.getClassName().toString())) {
            if (seen[0] == want) return n;
            seen[0]++;
        }
        for (int i = 0; i < n.getChildCount(); i++) {
            AccessibilityNodeInfo r = nthOfClass(n.getChild(i), cls, want, seen);
            if (r != null) return r;
        }
        return null;
    }

    private static int ordinalOf(AccessibilityNodeInfo root, AccessibilityNodeInfo target, String cls) {
        int[] seen = {0};
        return countUntil(root, target, cls, seen) ? seen[0] : 0;
    }

    private static boolean countUntil(AccessibilityNodeInfo n, AccessibilityNodeInfo target, String cls, int[] seen) {
        if (n == null) return false;
        if (n.getClassName() != null && cls.equals(n.getClassName().toString())) {
            if (n.equals(target)) return true;
            seen[0]++;
        }
        for (int i = 0; i < n.getChildCount(); i++) if (countUntil(n.getChild(i), target, cls, seen)) return true;
        return false;
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

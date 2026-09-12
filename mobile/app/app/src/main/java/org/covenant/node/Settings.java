package org.covenant.node;

import android.content.Context;

import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;

/**
 * One settings file shared by the Activity (main process), the Service (the
 * ":node" process) and the boot receiver. Plain JSON on disk with tmp+rename,
 * not SharedPreferences, because SharedPreferences is not safe across
 * processes. Unreadable or unparseable means defaults, never a crash.
 */
final class Settings {
    String pcPeer = "";
    int port = 5000;
    String nodeId = "phone";
    boolean autostart = false;

    static File file(Context c) { return new File(c.getFilesDir(), "settings.json"); }

    static Settings load(Context c) {
        Settings s = new Settings();
        try {
            String raw = new String(Files.readAllBytes(file(c).toPath()), StandardCharsets.UTF_8);
            JSONObject j = new JSONObject(raw);
            s.pcPeer = j.optString("pc_peer", s.pcPeer);
            s.port = j.optInt("port", s.port);
            s.nodeId = j.optString("node_id", s.nodeId);
            s.autostart = j.optBoolean("autostart", s.autostart);
        } catch (Exception ignored) {
            // absent on first run, or damaged: defaults
        }
        return s;
    }

    static void save(Context c, Settings s) throws Exception {
        JSONObject j = new JSONObject();
        j.put("pc_peer", s.pcPeer);
        j.put("port", s.port);
        j.put("node_id", s.nodeId);
        j.put("autostart", s.autostart);
        File tmp = new File(c.getFilesDir(), "settings.json.tmp");
        try (OutputStreamWriter w = new OutputStreamWriter(new FileOutputStream(tmp), StandardCharsets.UTF_8)) {
            w.write(j.toString(1));
        }
        if (!tmp.renameTo(file(c))) throw new Exception("could not replace settings.json");
    }

    /** Empty, or host:port with exactly one ':' and 1..65535 (the node splits on ':'; IPv6 literals unsupported). */
    static boolean validPeer(String s) {
        if (s == null || s.trim().isEmpty()) return true;
        String t = s.trim();
        int i = t.indexOf(':');
        if (i <= 0 || i != t.lastIndexOf(':')) return false;
        try {
            int p = Integer.parseInt(t.substring(i + 1));
            return p >= 1 && p <= 65535;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /** The node also binds port+1 and port+11. */
    static boolean validPort(int p) { return p >= 1024 && p <= 65000; }
}

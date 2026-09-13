package org.covenant.node;

import android.content.Context;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.List;

/**
 * PHASE 2, the preliminary brain (the operator's decision, 2026-09-12, under
 * his rule that a phone is private to the person holding it): a recipe is
 * something the owner DID once in a green-lit app while the actuator watched
 * -- the taps, the text, the scrolls -- kept on this phone as files/recipes/
 * NAME.json. It learns in three plain ways, all local and all visible:
 *   1. every step keeps four locators for its target (view id, text,
 *      description, class+ordinal) with a score each; a replay tries the
 *      best-scored first, and a locator that found the target is scored up,
 *      one that missed is scored down -- so the recipe gets surer of what
 *      identifies each control, and survives a relabelled button;
 *   2. text the owner typed becomes a SLOT: the replay asks for it, so one
 *      demonstration of "post this" serves every later post;
 *   3. every run appends its outcome (which step, which locator, how long) to
 *      the recipe, so the owner can read what it knows and delete what it
 *      learned wrong.
 * No model, no network, no screen leaves the phone. Nothing here can act in
 * an app that is not green-lit, and every text filled goes through the gate.
 */
final class Recipe {
    static final class Step {
        String kind = "click";            // click | type | scroll
        String id = "", text = "", desc = "", cls = "";
        int ordinal = 0;                  // n-th node of that class on the screen, a last resort
        boolean slot = false;             // a type step whose text is asked for at run time
        double sId = 1.0, sText = 0.9, sDesc = 0.8, sCls = 0.3;   // locator scores, learned

        JSONObject toJson() throws Exception {
            JSONObject j = new JSONObject();
            j.put("kind", kind); j.put("id", id); j.put("text", text); j.put("desc", desc); j.put("cls", cls);
            j.put("ordinal", ordinal); j.put("slot", slot);
            j.put("scores", new JSONObject().put("id", sId).put("text", sText).put("desc", sDesc).put("cls", sCls));
            return j;
        }

        static Step fromJson(JSONObject j) {
            Step s = new Step();
            s.kind = j.optString("kind", "click"); s.id = j.optString("id", ""); s.text = j.optString("text", "");
            s.desc = j.optString("desc", ""); s.cls = j.optString("cls", ""); s.ordinal = j.optInt("ordinal", 0);
            s.slot = j.optBoolean("slot", false);
            JSONObject sc = j.optJSONObject("scores");
            if (sc != null) { s.sId = sc.optDouble("id", 1); s.sText = sc.optDouble("text", .9); s.sDesc = sc.optDouble("desc", .8); s.sCls = sc.optDouble("cls", .3); }
            return s;
        }

        /** The locators in the order the recipe currently trusts them. */
        List<String> order() {
            List<String> names = new ArrayList<>();
            double[][] pairs = {{sId, 0}, {sText, 1}, {sDesc, 2}, {sCls, 3}};
            String[] label = {"id", "text", "desc", "cls"};
            boolean[] used = new boolean[4];
            for (int k = 0; k < 4; k++) {
                int best = -1;
                for (int i = 0; i < 4; i++) if (!used[i] && (best < 0 || pairs[i][0] > pairs[best][0])) best = i;
                used[best] = true;
                boolean have = best == 0 ? !id.isEmpty() : best == 1 ? !text.isEmpty() : best == 2 ? !desc.isEmpty() : !cls.isEmpty();
                if (have) names.add(label[best]);
            }
            return names;
        }

        void learn(String locator, boolean hit) {
            double d = hit ? 0.15 : -0.25;
            if (locator.equals("id")) sId = clamp(sId + d);
            else if (locator.equals("text")) sText = clamp(sText + d);
            else if (locator.equals("desc")) sDesc = clamp(sDesc + d);
            else sCls = clamp(sCls + d);
        }

        private static double clamp(double v) { return Math.max(0.05, Math.min(2.0, v)); }

        String describe() {
            String target = !id.isEmpty() ? id.substring(id.indexOf('/') + 1) : !text.isEmpty() ? "\"" + text + "\"" : !desc.isEmpty() ? desc : cls + "#" + ordinal;
            return kind + " " + target + (slot ? " [slot]" : (kind.equals("type") ? " = \"" + text + "\"" : ""));
        }
    }

    String name = "", pkg = "";
    long created = System.currentTimeMillis();
    final List<Step> steps = new ArrayList<>();
    final List<String> runs = new ArrayList<>();          // one line per replay, newest last
    String lastAnswer = "";                                // what the app showed when the last run finished (kept on the phone)

    static File dir(Context c) { File d = new File(c.getFilesDir(), "recipes"); d.mkdirs(); return d; }
    File file(Context c) { return new File(dir(c), name.replaceAll("[^A-Za-z0-9._-]", "_") + ".json"); }

    static List<Recipe> all(Context c) {
        List<Recipe> out = new ArrayList<>();
        File[] fs = dir(c).listFiles();
        if (fs == null) return out;
        for (File f : fs) {
            if (!f.getName().endsWith(".json")) continue;
            try { out.add(load(f)); } catch (Exception ignored) { }
        }
        return out;
    }

    static Recipe load(File f) throws Exception {
        JSONObject j = new JSONObject(new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8));
        Recipe r = new Recipe();
        r.name = j.optString("name"); r.pkg = j.optString("pkg"); r.created = j.optLong("created", 0);
        JSONArray st = j.optJSONArray("steps");
        for (int i = 0; st != null && i < st.length(); i++) r.steps.add(Step.fromJson(st.getJSONObject(i)));
        JSONArray ru = j.optJSONArray("runs");
        for (int i = 0; ru != null && i < ru.length(); i++) r.runs.add(ru.getString(i));
        r.lastAnswer = j.optString("last_answer", "");
        return r;
    }

    void save(Context c) throws Exception {
        JSONObject j = new JSONObject();
        j.put("name", name); j.put("pkg", pkg); j.put("created", created);
        JSONArray st = new JSONArray();
        for (Step s : steps) st.put(s.toJson());
        j.put("steps", st);
        while (runs.size() > 40) runs.remove(0);
        j.put("runs", new JSONArray(runs));
        j.put("last_answer", lastAnswer);
        File tmp = new File(dir(c), file(c).getName() + ".tmp");
        try (OutputStreamWriter w = new OutputStreamWriter(new FileOutputStream(tmp), StandardCharsets.UTF_8)) {
            w.write(j.toString(1));
        }
        if (!tmp.renameTo(file(c))) throw new Exception("could not write the recipe");
    }

    boolean hasSlot() { for (Step s : steps) if (s.slot) return true; return false; }
}

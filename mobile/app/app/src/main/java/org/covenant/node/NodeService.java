package org.covenant.node;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.os.IBinder;
import android.os.PowerManager;
import android.util.Log;

import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

/**
 * The foreground service that runs the node. It lives in its own process
 * (":node", see the manifest) so that Stop can end the Python interpreter
 * cleanly -- Chaquopy has no documented way to stop and restart Python inside
 * one process -- and so the UI process never has to start Python at all.
 *
 * Order of business, and the rules behind it (all verified against
 * developer.android.com by the research that designed this file):
 *   1. startForeground within five seconds of being started, or Android kills
 *      the service and calls it an ANR. Type specialUse: no Android 15 timeout,
 *      may be started from BOOT_COMPLETED.
 *   2. Hold a partial wake lock for the service's life: peers must be answered
 *      with the screen off. Documented battery cost; the operator chose uptime.
 *   3. Start Python once, on a dedicated thread, and run entry.main, which
 *      blocks for the life of the node.
 *   4. When main returns or raises the node exited for a reason entry.py wrote
 *      to last_exit.txt; stop and let the UI show why. No restart loop here:
 *      START_STICKY restarts an OS kill, a user Stop stays stopped.
 */
public class NodeService extends Service {
    static final String CHANNEL = "node";
    static final int NOTIF_ID = 1;
    static final String ACTION_STOP = "org.covenant.node.STOP";

    private PowerManager.WakeLock wakeLock;
    private Thread nodeThread;

    @Override
    public void onCreate() {
        super.onCreate();
        NotificationManager nm = getSystemService(NotificationManager.class);
        nm.createNotificationChannel(new NotificationChannel(CHANNEL, "Covenant node", NotificationManager.IMPORTANCE_LOW));
    }

    private Notification notif(String text) {
        int port = Settings.load(this).port;
        PendingIntent open = PendingIntent.getActivity(this, 0, new Intent(this, MainActivity.class), PendingIntent.FLAG_IMMUTABLE);
        PendingIntent stop = PendingIntent.getService(this, 1, new Intent(this, NodeService.class).setAction(ACTION_STOP), PendingIntent.FLAG_IMMUTABLE);
        return new Notification.Builder(this, CHANNEL)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentTitle("Covenant node")
                .setContentText(text + "  http://127.0.0.1:" + port + "/health")
                .setContentIntent(open)
                .addAction(new Notification.Action.Builder(null, "Stop", stop).build())
                .setOngoing(true)
                .build();
    }

    @Override
    public int onStartCommand(Intent i, int flags, int startId) {
        if (i != null && ACTION_STOP.equals(i.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }
        // FIRST: the five-second rule.
        startForeground(NOTIF_ID, notif("starting"), ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE);
        if (wakeLock == null) {
            wakeLock = getSystemService(PowerManager.class).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "covenant:node");
            wakeLock.setReferenceCounted(false);
            wakeLock.acquire();   // no timeout: the node answers peers with the screen off
        }
        if (nodeThread != null && nodeThread.isAlive()) return START_STICKY;   // Start pressed twice
        nodeThread = new Thread(this::runNode, "covenant-node");
        nodeThread.start();
        return START_STICKY;
    }

    private void runNode() {
        try {
            if (!Python.isStarted()) Python.start(new AndroidPlatform(this));
            getSystemService(NotificationManager.class).notify(NOTIF_ID, notif("running"));
            // Blocks for the life of the node.
            Python.getInstance().getModule("entry").callAttr("main",
                    getFilesDir().getAbsolutePath(), getApplicationInfo().sourceDir);
        } catch (Throwable t) {
            Log.e("covenant", "node thread ended", t);
        }
        // main() returned or raised: the node exited for a reason entry.py recorded.
        stopSelf();
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) wakeLock.release();
        stopForeground(STOP_FOREGROUND_REMOVE);
        super.onDestroy();
        // The only clean way to end a Python main thread parked in `while True: sleep(1)`.
        // A stopped service is not auto-restarted; an OS kill is (START_STICKY).
        android.os.Process.killProcess(android.os.Process.myPid());
    }

    @Override
    public IBinder onBind(Intent i) { return null; }
}

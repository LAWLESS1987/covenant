package org.covenant.node;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * Restart the node after a reboot or an in-place update, but only if the
 * operator ticked "Start at boot" (default off, so this is inert until chosen).
 * Starting a specialUse foreground service from BOOT_COMPLETED is permitted on
 * target 35; a dataSync one would not be.
 */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent i) {
        String a = i.getAction();
        if (!Intent.ACTION_BOOT_COMPLETED.equals(a) && !Intent.ACTION_MY_PACKAGE_REPLACED.equals(a)) return;
        if (!Settings.load(c).autostart) return;
        c.startForegroundService(new Intent(c, NodeService.class));
    }
}

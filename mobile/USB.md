# The phone on a cable: install and peer over USB-C

Asked 2026-09-12: "can we set it up to download via c to c port ... tethered".
Yes. A data cable and Android's own debug bridge replace three things that kept
failing: the QR the camera would not read, the browser download with its
"unknown sources" prompt, and a Wi-Fi peer address behind a firewall rule that
was never added.

## Once, on the phone

1. Settings > About phone > Software information > tap **Build number** seven times.
2. Settings > Developer options > **USB debugging** on.
3. Plug in a **data** cable (many USB-C cables are charge-only and show nothing).
4. The phone asks "Allow USB debugging?" with this PC's fingerprint. Tick
   **Always allow from this computer**, tap OK.

## On the PC

```
python mobile/usb_link.py status
python mobile/usb_link.py link
python mobile/usb_link.py install covenant.apk
python mobile/usb_link.py unlink
```

`status` says what adb sees and, when it cannot use the phone, why -- no cable,
unauthorised, offline, two phones. `link` sets two tunnels:

| tunnel | meaning |
|---|---|
| `adb reverse tcp:15001 tcp:5001` | the phone's `127.0.0.1:15001` is this PC's node A peer port. The phone node peers with **`PC_PEER=127.0.0.1:15001`**. |
| `adb forward tcp:15000 tcp:5000` | this PC's `127.0.0.1:15000` is the phone node's API: **http://127.0.0.1:15000/health** reads the phone from here. |

15001 on the phone side because the phone node's own peer port is 5001 (its API
port plus one) and the tunnel must not sit on it; 15000 on the PC side because
node A holds 5000 here. Neither crosses Windows Firewall -- adb opens the
PC-side socket itself, from this machine, to localhost -- so the 5001 inbound
rule that Wi-Fi peering needs is not needed for the cable.

Tunnels last until the cable is unplugged or `unlink`. `install -r` updates an
existing install in place and never grants permissions (`-g` is not used).

## adb

`link`/`status`/`install` need Google's platform-tools. If `tools/platform-tools/`
is absent the script says so and downloads `platform-tools-latest-windows.zip`
from `https://dl.google.com/android/repository/` (7.7 MB, measured 2026-09-12)
into that gitignored folder -- no installer, nothing system-wide, PATH untouched.
`--no-download` refuses; `--adb PATH` points at your own.

## What it is not

It is not USB tethering. Samsung's "USB tethering" setting turns the cable into
a network with an address the PC would have to discover each time, and the
inbound firewall rule would then apply to that adapter too. The debug bridge
does the same job with fixed loopback addresses and no rule. If you want the
tethering route as well, say so; `usb_link.py` does not touch that setting.

Measured 2026-09-12 with no phone attached: `status` exits 2 and names the
cause. The tunnels and install paths are pinned by `test_m4_usb_link.py`, which
drives the tool with a stub adb and reads every argument list it issues.

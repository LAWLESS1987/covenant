# covenant self-evaluation ledger
# For Misha, and all that were lost to injustice.
# One block per evaluation: PASS/WARN/FAIL per layer, worst wins.
# Written by covenant_watchdog.py (report-only) and by the scheduled
# covenant-self-eval task. Append-only; rotates to .prev at 512KB.

## 2026-10-21T00:57:51Z  overall WARN  (round 43320)
nodes     PASS  3/3 up, height 99 (spread 0), source 08c05f7c537f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: highway: ambassador_stalled is present and nothing here repairs it -- {"paused": true, "last_live_round_h": 15
trader    PASS  log 12.0h old; freshness exit 0: RAN: a cycle dated 2026-10-20 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (16h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.1h ago; 89 file(s) not committed
disk      PASS  166G free of 476G (65% used); logs/ 39M; repository 30.6M stored
daily     WARN  15.9h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T02:06:54Z  overall WARN  (round 43380)
nodes     PASS  3/3 up, height 99 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 13.1h old; freshness exit 0: RAN: a cycle dated 2026-10-20 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (18h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.3h ago; 89 file(s) not committed
disk      PASS  165G free of 476G (65% used); logs/ 39M; repository 30.6M stored
daily     WARN  17.0h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T03:15:38Z  overall WARN  (round 43440)
nodes     PASS  3/3 up, height 99 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 2
trader    PASS  log 14.3h old; freshness exit 0: RAN: a cycle dated 2026-10-20 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (19h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.4h ago; 89 file(s) not committed
disk      PASS  165G free of 476G (65% used); logs/ 40M; repository 30.6M stored
daily     WARN  18.2h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T04:24:07Z  overall WARN  (round 43500)
nodes     PASS  3/3 up, height 99 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 5
trader    PASS  log 15.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (20h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.5h ago; 89 file(s) not committed
disk      PASS  164G free of 476G (65% used); logs/ 40M; repository 30.6M stored
daily     WARN  19.3h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T05:33:08Z  overall WARN  (round 43560)
nodes     PASS  3/3 up, height 99 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 4
trader    PASS  log 16.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (21h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 13.7h ago; 89 file(s) not committed
disk      PASS  164G free of 476G (65% used); logs/ 41M; repository 30.6M stored
daily     WARN  20.5h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T06:42:06Z  overall WARN  (round 43620)
nodes     PASS  3/3 up, height 99 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 4
trader    PASS  log 17.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (22h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.8h ago; 89 file(s) not committed
disk      PASS  163G free of 476G (65% used); logs/ 41M; repository 30.6M stored
daily     WARN  21.6h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T07:49:55Z  overall WARN  (round 43680)
nodes     PASS  3/3 up, height 100 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 18.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-20T08:28:20Z REFUSED (23h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 16.0h ago; 90 file(s) not committed
disk      PASS  162G free of 476G (66% used); logs/ 42M; repository 30.6M stored
daily     WARN  22.8h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T08:56:39Z  overall WARN  (round 43740)
nodes     PASS  3/3 up, height 100 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 1
trader    PASS  log 19.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (1h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD dbb4fba, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 17.1h ago; 92 file(s) not committed
disk      PASS  161G free of 476G (66% used); logs/ 42M; repository 29.0M stored
daily     WARN  23.9h ago: PC node degraded | phone node healthy | sync verified | tests PASS | regressions PASS | new failures 0 | rolled back 0

## 2026-10-21T10:08:44Z  overall FAIL  (round 43800)
nodes     PASS  3/3 up, height 100 (spread 0), source 2e31e18595fc
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 2e31e18595fc, peers report ['08c05f7c537f'] (last heard 8
trader    PASS  log 21.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (2h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 2e31e18595fc matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 40c4012, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 92 file(s) not committed
disk      PASS  159G free of 476G (66% used); logs/ 42M; repository 29.2M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T11:19:54Z  overall FAIL  (round 43860)
nodes     PASS  3/3 up, height 100 (spread 0), source 3ce0f86f961a
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: restarted since the last check (uptime went backwards)
trader    PASS  log 22.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (3h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 3ce0f86f961a matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 48aedc4, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 93 file(s) not committed
disk      PASS  159G free of 476G (66% used); logs/ 41M; repository 29.8M stored
daily     FAIL  1.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T12:29:45Z  overall FAIL  (round 43920)
nodes     PASS  3/3 up, height 100 (spread 0), source 3ce0f86f961a
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 3ce0f86f961a, peers report ['08c05f7c537f'] (last heard 2
trader    PASS  log 23.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (4h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 3ce0f86f961a matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e21e028, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.1h ago; 92 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 42M; repository 30.0M stored
daily     FAIL  3.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T13:36:46Z  overall FAIL  (round 43980)
nodes     PASS  3/3 up, height 101 (spread 0), source 3ce0f86f961a
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 0.6h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (5h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 3ce0f86f961a matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e21e028, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.2h ago; 92 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 42M; repository 30.0M stored
daily     FAIL  4.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T14:45:24Z  overall FAIL  (round 44040)
nodes     PASS  3/3 up, height 101 (spread 0), source 3ce0f86f961a
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 3ce0f86f961a, peers report ['08c05f7c537f'] (last heard 7
trader    PASS  log 1.8h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (7h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 3ce0f86f961a matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e21e028, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.4h ago; 92 file(s) not committed
disk      PASS  161G free of 476G (66% used); logs/ 43M; repository 30.0M stored
daily     FAIL  5.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T15:51:19Z  overall FAIL  (round 44100)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 1
trader    PASS  log 2.9h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (8h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 708233c, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.4h ago; 92 file(s) not committed
disk      PASS  160G free of 476G (66% used); logs/ 42M; repository 30.4M stored
daily     FAIL  6.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T16:58:39Z  overall FAIL  (round 44160)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 7
trader    PASS  log 4.0h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (9h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 708233c, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.5h ago; 95 file(s) not committed
disk      PASS  159G free of 476G (66% used); logs/ 43M; repository 30.4M stored
daily     FAIL  7.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T18:05:48Z  overall FAIL  (round 44220)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 2
trader    PASS  log 5.1h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (10h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD d44eff6, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.7h ago; 92 file(s) not committed
disk      PASS  157G free of 476G (66% used); logs/ 43M; repository 30.7M stored
daily     FAIL  8.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T19:11:09Z  overall FAIL  (round 44280)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 1
trader    PASS  log 6.2h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (11h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 32e4cab, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.7h ago; 92 file(s) not committed
disk      PASS  157G free of 476G (66% used); logs/ 44M; repository 30.8M stored
daily     FAIL  9.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T20:16:12Z  overall FAIL  (round 44340)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 4
trader    PASS  log 7.3h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (12h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7d62162, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.8h ago; 92 file(s) not committed
disk      PASS  157G free of 476G (67% used); logs/ 44M; repository 30.9M stored
daily     FAIL  10.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T21:21:31Z  overall FAIL  (round 44400)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 4
trader    PASS  log 8.4h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (13h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 897a996, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.9h ago; 92 file(s) not committed
disk      PASS  156G free of 476G (67% used); logs/ 44M; repository 31.0M stored
daily     FAIL  12.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T22:26:22Z  overall FAIL  (round 44460)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 5
trader    PASS  log 9.4h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (14h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 897a996, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.0h ago; 92 file(s) not committed
disk      PASS  156G free of 476G (67% used); logs/ 44M; repository 31.0M stored
daily     FAIL  13.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-21T23:34:02Z  overall FAIL  (round 44520)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 10.6h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (15h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 6f0ab3022b44 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 5e89272, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 92 file(s) not committed
disk      PASS  155G free of 476G (67% used); logs/ 45M; repository 31.1M stored
daily     FAIL  14.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T00:41:19Z  overall FAIL  (round 44580)
nodes     PASS  3/3 up, height 101 (spread 0), source 6f0ab3022b44
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are 6f0ab3022b44, peers report ['08c05f7c537f'] (last heard 1
trader    PASS  log 11.7h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (16h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3ebdfbf, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.2h ago; 93 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 45M; repository 31.8M stored
daily     FAIL  15.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T01:53:08Z  overall FAIL  (round 44640)
nodes     PASS  3/3 up, height 101 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 12.9h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (18h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3ebdfbf, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.4h ago; 93 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 45M; repository 31.8M stored
daily     FAIL  16.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T03:03:54Z  overall FAIL  (round 44700)
nodes     PASS  3/3 up, height 101 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 14.1h old; freshness exit 0: RAN: a cycle dated 2026-10-21 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (19h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3ebdfbf, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.6h ago; 93 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 45M; repository 31.8M stored
daily     FAIL  17.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T04:20:10Z  overall FAIL  (round 44760)
nodes     PASS  3/3 up, height 101 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 4
trader    PASS  log 15.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (20h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3ebdfbf, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.9h ago; 93 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 45M; repository 31.8M stored
daily     FAIL  18.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T05:30:00Z  overall FAIL  (round 44820)
nodes     PASS  3/3 up, height 101 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 16.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (21h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3ebdfbf, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.1h ago; 94 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 41M; repository 31.8M stored
daily     FAIL  20.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T06:39:30Z  overall FAIL  (round 44880)
nodes     PASS  3/3 up, height 101 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: anomaly SPIKE -- peer_message_error (recent 11 vs expected 1.6)
trader    PASS  log 17.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (22h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3ebdfbf, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 15.2h ago; 94 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 41M; repository 31.8M stored
daily     FAIL  21.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T07:50:58Z  overall FAIL  (round 44940)
nodes     PASS  3/3 up, height 102 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 2
trader    PASS  log 18.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-21T08:14:34Z REFUSED (24h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 16.4h ago; 95 file(s) not committed
disk      PASS  155G free of 476G (67% used); logs/ 41M; repository 32.0M stored
daily     FAIL  22.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T09:02:44Z  overall FAIL  (round 45000)
nodes     PASS  3/3 up, height 102 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 7
trader    PASS  log 20.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (0h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 17.6h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 42M; repository 29.1M stored
daily     FAIL  23.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-22T10:09:32Z  overall FAIL  (round 45060)
nodes     PASS  3/3 up, height 102 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 21.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (2h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 42M; repository 29.1M stored
daily     FAIL  0.6h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T11:16:59Z  overall FAIL  (round 45120)
nodes     PASS  3/3 up, height 102 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 22.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (3h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.8h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 42M; repository 29.1M stored
daily     FAIL  1.8h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T12:23:58Z  overall FAIL  (round 45180)
nodes     PASS  3/3 up, height 102 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 23.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (4h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.9h ago; 95 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 43M; repository 29.1M stored
daily     FAIL  2.9h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T13:31:12Z  overall FAIL  (round 45240)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 0.5h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (5h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 43M; repository 29.1M stored
daily     FAIL  4.0h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T14:38:10Z  overall FAIL  (round 45300)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 1.6h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (6h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ea93365, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 95 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 43M; repository 29.1M stored
daily     FAIL  5.1h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T15:45:27Z  overall FAIL  (round 45360)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 2.8h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (7h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 9e7f886, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.3h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 43M; repository 29.2M stored
daily     FAIL  6.2h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T16:55:03Z  overall FAIL  (round 45420)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 3.9h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (8h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ee2d961, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.4h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 44M; repository 29.4M stored
daily     FAIL  7.4h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T18:02:21Z  overall FAIL  (round 45480)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 5.0h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (9h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 8de62a7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.5h ago; 95 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 44M; repository 30.8M stored
daily     FAIL  8.5h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T19:09:48Z  overall FAIL  (round 45540)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 64c5eebd810e, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 6.2h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (11h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3c24e48, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.7h ago; 95 file(s) not committed
disk      PASS  155G free of 476G (67% used); logs/ 45M; repository 31.0M stored
daily     FAIL  9.7h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T20:14:43Z  overall FAIL  (round 45600)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 7.2h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (12h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3c24e48, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.7h ago; 95 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 45M; repository 31.0M stored
daily     FAIL  10.7h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T21:23:35Z  overall FAIL  (round 45660)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 8.4h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (13h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3c24e48, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.9h ago; 95 file(s) not committed
disk      PASS  152G free of 476G (67% used); logs/ 45M; repository 31.0M stored
daily     FAIL  11.9h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T22:30:29Z  overall FAIL  (round 45720)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 9.5h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (14h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 3c24e48, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 13.0h ago; 95 file(s) not committed
disk      PASS  152G free of 476G (68% used); logs/ 46M; repository 31.0M stored
daily     FAIL  13.0h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-22T23:37:49Z  overall FAIL  (round 45780)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 10.6h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (15h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 2b1de79, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.1h ago; 95 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 46M; repository 31.7M stored
daily     FAIL  14.1h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T00:46:09Z  overall FAIL  (round 45840)
nodes     PASS  3/3 up, height 103 (spread 0), source 64c5eebd810e
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 11.8h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (16h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core 64c5eebd810e matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b13fc71, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 15.3h ago; 95 file(s) not committed
disk      PASS  146G free of 476G (69% used); logs/ 47M; repository 31.8M stored
daily     FAIL  15.3h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T01:50:19Z  overall FAIL  (round 45900)
nodes     PASS  3/3 up, height 103 (spread 0), source 223bcb612fce
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 12.8h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (17h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 16.3h ago; 98 file(s) not committed
disk      PASS  151G free of 476G (68% used); logs/ 44M; repository 34.8M stored
daily     FAIL  16.3h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T03:02:30Z  overall FAIL  (round 45960)
nodes     PASS  3/3 up, height 103 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 7
trader    PASS  log 14.0h old; freshness exit 0: RAN: a cycle dated 2026-10-22 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (18h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 17.5h ago; 98 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 44M; repository 34.8M stored
daily     FAIL  17.5h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T04:07:56Z  overall FAIL  (round 46020)
nodes     PASS  3/3 up, height 103 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 2
trader    PASS  log 15.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (20h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 18.6h ago; 98 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 45M; repository 34.8M stored
daily     FAIL  18.6h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T05:15:40Z  overall FAIL  (round 46080)
nodes     PASS  3/3 up, height 103 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 1
trader    PASS  log 16.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (21h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 19.8h ago; 98 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 45M; repository 34.8M stored
daily     FAIL  19.8h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T06:22:54Z  overall FAIL  (round 46140)
nodes     PASS  3/3 up, height 103 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 3
trader    PASS  log 17.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (22h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 20.9h ago; 98 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 45M; repository 34.8M stored
daily     FAIL  20.9h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T07:27:51Z  overall FAIL  (round 46200)
nodes     PASS  3/3 up, height 103 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 2
trader    PASS  log 18.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (23h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 22.0h ago; 98 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 45M; repository 34.8M stored
daily     FAIL  22.0h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T08:41:24Z  overall FAIL  (round 46260)
nodes     PASS  3/3 up, height 104 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 6
trader    PASS  log 19.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-22T08:34:58Z REFUSED (24h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 23.2h ago; 99 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 46M; repository 29.2M stored
daily     FAIL  23.2h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T09:46:26Z  overall FAIL  (round 46320)
nodes     PASS  3/3 up, height 104 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['08c05f7c537f'] (last heard 5
trader    PASS  log 20.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (1h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 24.3h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 46M; repository 29.2M stored
daily     FAIL  24.3h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions PASS | new failures 8 | rolled back 0

## 2026-10-23T10:59:55Z  overall FAIL  (round 46380)
nodes     PASS  3/3 up, height 104 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 22.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (2h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 0.6h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 47M; repository 29.2M stored
daily     FAIL  0.6h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T12:04:50Z  overall FAIL  (round 46440)
nodes     PASS  3/3 up, height 104 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 23.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (3h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 1.7h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 47M; repository 29.2M stored
daily     FAIL  1.7h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T13:16:10Z  overall FAIL  (round 46500)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 0.3h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (5h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 2.9h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 47M; repository 29.2M stored
daily     FAIL  2.9h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T14:27:01Z  overall FAIL  (round 46560)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 1.4h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (6h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 4.1h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 47M; repository 29.2M stored
daily     FAIL  4.1h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T15:39:00Z  overall FAIL  (round 46620)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 3
trader    PASS  log 2.6h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (7h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 5.3h ago; 100 file(s) not committed
disk      PASS  148G free of 476G (68% used); logs/ 48M; repository 29.2M stored
daily     FAIL  5.3h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T16:50:35Z  overall FAIL  (round 46680)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 1
trader    PASS  log 3.8h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (8h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 6.5h ago; 100 file(s) not committed
disk      PASS  147G free of 476G (69% used); logs/ 48M; repository 29.2M stored
daily     FAIL  6.5h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T18:07:55Z  overall FAIL  (round 46740)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 5
trader    PASS  log 5.1h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (9h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 7.8h ago; 100 file(s) not committed
disk      PASS  151G free of 476G (68% used); logs/ 48M; repository 29.2M stored
daily     FAIL  7.8h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T19:19:30Z  overall FAIL  (round 46800)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 2
trader    PASS  log 6.3h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (11h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 9.0h ago; 100 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 48M; repository 29.2M stored
daily     FAIL  9.0h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T20:29:31Z  overall FAIL  (round 46860)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 3
trader    PASS  log 7.5h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (12h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 10.1h ago; 100 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 48M; repository 29.2M stored
daily     FAIL  10.1h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T21:40:44Z  overall FAIL  (round 46920)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 2
trader    PASS  log 8.7h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (13h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 11.3h ago; 100 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 49M; repository 29.2M stored
daily     FAIL  11.3h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-23T22:51:27Z  overall FAIL  (round 46980)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 2
trader    PASS  log 9.9h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (14h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 12.5h ago; 100 file(s) not committed
disk      PASS  152G free of 476G (67% used); logs/ 49M; repository 29.2M stored
daily     FAIL  12.5h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T00:07:02Z  overall FAIL  (round 47040)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 1
trader    PASS  log 11.1h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (15h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 13.8h ago; 100 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 49M; repository 29.2M stored
daily     FAIL  13.8h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T01:17:31Z  overall FAIL  (round 47100)
nodes     PASS  3/3 up, height 105 (spread 0), source 09fc318785ba
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 09fc318785ba, peers report ['223bcb612fce'] (last heard 2
trader    PASS  log 12.3h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (17h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core 09fc318785ba (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 64c5eebd810e, the core is 09fc318785ba; EXPECTED_LINES is 13474, the core has 13485 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 6970047, 0 ahead / 1 behind origin/main as of the last fetch; last fetch 14.9h ago; 100 file(s) not committed
disk      PASS  152G free of 476G (67% used); logs/ 49M; repository 29.2M stored
daily     FAIL  14.9h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T02:27:10Z  overall FAIL  (round 47160)
nodes     PASS  3/3 up, height 105 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: moltbook_strikes is present and nothing here repairs it -- {"run": 5, "warn_at": 5, "suspends_at": 10
trader    PASS  log 13.5h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (18h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.9h ago; 100 file(s) not committed
disk      PASS  151G free of 476G (68% used); logs/ 48M; repository 29.8M stored
daily     FAIL  16.1h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T03:36:52Z  overall FAIL  (round 47220)
nodes     PASS  3/3 up, height 105 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: anomaly SPIKE -- peer_message_error (recent 6 vs expected 1.9)
trader    PASS  log 14.6h old; freshness exit 0: RAN: a cycle dated 2026-10-23 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (19h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.1h ago; 100 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 48M; repository 29.8M stored
daily     FAIL  17.3h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T04:47:37Z  overall FAIL  (round 47280)
nodes     PASS  3/3 up, height 105 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 15.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (20h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.3h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 48M; repository 29.8M stored
daily     FAIL  18.4h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T06:03:14Z  overall FAIL  (round 47340)
nodes     PASS  3/3 up, height 105 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: road_stalled is present and break_stall held -- nothing a retry can break -- waiting on their own gro
trader    PASS  log 17.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (21h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.5h ago; 100 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 48M; repository 29.8M stored
daily     FAIL  19.7h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T07:13:21Z  overall FAIL  (round 47400)
nodes     PASS  3/3 up, height 105 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: road_stalled is present and break_stall held -- nothing a retry can break -- waiting on their own gro
trader    PASS  log 18.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (23h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.7h ago; 100 file(s) not committed
disk      PASS  151G free of 476G (68% used); logs/ 48M; repository 29.8M stored
daily     FAIL  20.9h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T08:24:40Z  overall FAIL  (round 47460)
nodes     PASS  3/3 up, height 106 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 19.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-23T08:43:02Z REFUSED (24h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.9h ago; 101 file(s) not committed
disk      PASS  146G free of 476G (69% used); logs/ 48M; repository 29.1M stored
daily     FAIL  22.0h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T09:35:55Z  overall FAIL  (round 47520)
nodes     PASS  3/3 up, height 106 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 20.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 102 file(s) not committed
disk      PASS  145G free of 476G (69% used); logs/ 49M; repository 29.1M stored
daily     FAIL  23.2h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T10:47:29Z  overall FAIL  (round 47580)
nodes     PASS  3/3 up, height 106 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: ambassador_stalled is present and nothing here repairs it -- {"paused": true, "last_live_round_h": 0.
trader    PASS  log 21.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.3h ago; 102 file(s) not committed
disk      PASS  144G free of 476G (69% used); logs/ 49M; repository 29.1M stored
daily     FAIL  24.4h ago: PC node degraded | phone node degraded | sync verified | tests FAIL | regressions FAIL | new failures 8 | rolled back 0

## 2026-10-24T12:01:40Z  overall FAIL  (round 47640)
nodes     PASS  3/3 up, height 106 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 23.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 6f58c0f, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 102 file(s) not committed
disk      PASS  143G free of 476G (70% used); logs/ 44M; repository 29.1M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T13:15:49Z  overall FAIL  (round 47700)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 0.3h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 264d9b3, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 102 file(s) not committed
disk      PASS  98G free of 476G (79% used); logs/ 46M; repository 29.2M stored
daily     FAIL  1.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T14:29:52Z  overall FAIL  (round 47760)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 1.5h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD d668a77, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.2h ago; 105 file(s) not committed
disk      PASS  97G free of 476G (79% used); logs/ 45M; repository 29.5M stored
daily     FAIL  3.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T15:38:31Z  overall FAIL  (round 47820)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 2.6h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD d668a77, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.3h ago; 105 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 29.5M stored
daily     FAIL  4.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T16:43:12Z  overall FAIL  (round 47880)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 3.7h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD d668a77, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.4h ago; 105 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 29.5M stored
daily     FAIL  5.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T17:48:06Z  overall FAIL  (round 47940)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 4.8h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD d668a77, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.5h ago; 105 file(s) not committed
disk      PASS  95G free of 476G (80% used); logs/ 46M; repository 29.5M stored
daily     FAIL  6.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T18:52:58Z  overall FAIL  (round 48000)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: phone_build_behind_core is present and fetch_build held -- nothing newer to fetch -- still on build d
trader    PASS  log 5.9h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD d668a77, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.1h ago; 106 file(s) not committed
disk      PASS  94G free of 476G (80% used); logs/ 46M; repository 29.9M stored
daily     FAIL  7.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T19:57:59Z  overall FAIL  (round 48060)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 7.0h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 4e03983, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.4h ago; 108 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 30.1M stored
daily     FAIL  8.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T21:02:35Z  overall FAIL  (round 48120)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 8.0h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 4e03983, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.5h ago; 108 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 30.1M stored
daily     FAIL  9.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T22:07:06Z  overall FAIL  (round 48180)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: schedule_stalled is present and nothing here repairs it -- {"tasks": 5, "stalled": ["CovenantGuard mi
trader    PASS  log 9.1h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 4e03983, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.5h ago; 109 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 30.1M stored
daily     FAIL  10.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-24T23:11:33Z  overall FAIL  (round 48240)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 10.2h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 4e03983, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.6h ago; 109 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 30.1M stored
daily     FAIL  11.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T00:16:02Z  overall FAIL  (round 48300)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 11.3h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 4e03983, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.7h ago; 109 file(s) not committed
disk      PASS  96G free of 476G (79% used); logs/ 46M; repository 30.1M stored
daily     FAIL  12.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T01:25:42Z  overall FAIL  (round 48360)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.1071+3912734, and build 0.1.1080+7619893 is here and newer by 47.1 h -- open http://1
trader    PASS  log 12.4h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.9h ago; 108 file(s) not committed
disk      PASS  101G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     FAIL  14.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T02:31:30Z  overall WARN  (round 48420)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 13.5h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.8h ago; 109 file(s) not committed
disk      PASS  101G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     WARN  0.8h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T03:35:53Z  overall WARN  (round 48480)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 14.6h old; freshness exit 0: RAN: a cycle dated 2026-10-24 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 109 file(s) not committed
disk      PASS  101G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     WARN  1.9h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T04:40:31Z  overall WARN  (round 48540)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 15.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.0h ago; 109 file(s) not committed
disk      PASS  101G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     WARN  2.9h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T05:44:51Z  overall WARN  (round 48600)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 16.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 109 file(s) not committed
disk      PASS  101G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     WARN  4.0h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T06:49:13Z  overall WARN  (round 48660)
nodes     PASS  3/3 up, height 107 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 17.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 109 file(s) not committed
disk      PASS  102G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     WARN  5.1h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T07:53:45Z  overall WARN  (round 48720)
nodes     PASS  3/3 up, height 108 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 18.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-24T08:32:26Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.2h ago; 110 file(s) not committed
disk      PASS  102G free of 476G (78% used); logs/ 47M; repository 30.2M stored
daily     WARN  6.2h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T08:58:56Z  overall WARN  (round 48780)
nodes     PASS  3/3 up, height 108 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 20.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (0h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 7619893, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.3h ago; 110 file(s) not committed
disk      PASS  102G free of 476G (78% used); logs/ 47M; repository 29.2M stored
daily     WARN  7.3h ago: PC node degraded | phone node degraded | sync verified | tests PASS | regressions PASS | new failures 1 | rolled back 0

## 2026-10-25T10:09:30Z  overall FAIL  (round 48840)
nodes     PASS  3/3 up, height 108 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 21.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b610d31, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 110 file(s) not committed
disk      PASS  121G free of 476G (74% used); logs/ 47M; repository 29.3M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T11:14:14Z  overall FAIL  (round 48900)
nodes     PASS  3/3 up, height 108 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 22.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b610d31, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.8h ago; 110 file(s) not committed
disk      PASS  121G free of 476G (74% used); logs/ 47M; repository 29.3M stored
daily     FAIL  1.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T12:18:50Z  overall FAIL  (round 48960)
nodes     PASS  3/3 up, height 108 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 23.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b610d31, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.9h ago; 110 file(s) not committed
disk      PASS  121G free of 476G (74% used); logs/ 47M; repository 29.3M stored
daily     FAIL  2.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T13:24:46Z  overall FAIL  (round 49020)
nodes     PASS  3/3 up, height 109 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 0.4h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b610d31, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 111 file(s) not committed
disk      PASS  121G free of 476G (74% used); logs/ 47M; repository 29.3M stored
daily     FAIL  4.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T14:29:32Z  overall FAIL  (round 49080)
nodes     PASS  3/3 up, height 109 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 1.5h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b610d31, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 111 file(s) not committed
disk      PASS  126G free of 476G (73% used); logs/ 47M; repository 29.3M stored
daily     FAIL  5.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T15:34:25Z  overall FAIL  (round 49140)
nodes     PASS  3/3 up, height 109 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 2.6h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e0fa974, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.1h ago; 110 file(s) not committed
disk      PASS  133G free of 476G (71% used); logs/ 47M; repository 29.4M stored
daily     FAIL  6.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T16:39:32Z  overall FAIL  (round 49200)
nodes     PASS  3/3 up, height 109 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 3.7h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 78a0949, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.2h ago; 110 file(s) not committed
disk      PASS  133G free of 476G (72% used); logs/ 47M; repository 29.6M stored
daily     FAIL  7.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T17:44:18Z  overall FAIL  (round 49260)
nodes     PASS  3/3 up, height 109 (spread 0), source afb202a0d922
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 4.7h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core afb202a0d922 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b5a9e31, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.3h ago; 110 file(s) not committed
disk      PASS  133G free of 476G (72% used); logs/ 47M; repository 29.8M stored
daily     FAIL  8.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T18:50:44Z  overall FAIL  (round 49320)
nodes     PASS  3/3 up, height 109 (spread 0), source a9a03a161427
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are a9a03a161427, peers report ['afb202a0d922'] (last heard 9
trader    PASS  log 5.8h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core a9a03a161427 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e775f9a, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.4h ago; 110 file(s) not committed
disk      PASS  130G free of 476G (72% used); logs/ 48M; repository 30.2M stored
daily     FAIL  9.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T19:58:01Z  overall FAIL  (round 49380)
nodes     PASS  3/3 up, height 109 (spread 0), source a9a03a161427
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: schedule_stalled is present and nothing here repairs it -- {"tasks": 5, "stalled": ["CovenantGuard mi
trader    PASS  log 7.0h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core a9a03a161427 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e775f9a, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.5h ago; 110 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 48M; repository 30.2M stored
daily     FAIL  10.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T21:02:01Z  overall FAIL  (round 49440)
nodes     PASS  3/3 up, height 109 (spread 0), source 9c346c06b891
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 9c346c06b891, peers report ['a9a03a161427'] (last heard 6
trader    PASS  log 8.0h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9c346c06b891 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD f4cf604, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.6h ago; 110 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 48M; repository 30.8M stored
daily     FAIL  11.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T22:07:02Z  overall FAIL  (round 49500)
nodes     PASS  3/3 up, height 109 (spread 0), source 9c346c06b891
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 9c346c06b891, peers report ['a9a03a161427'] (last heard 2
trader    PASS  log 9.1h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9c346c06b891 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 52b1770, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.7h ago; 110 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 48M; repository 30.9M stored
daily     FAIL  12.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-25T23:11:43Z  overall FAIL  (round 49560)
nodes     PASS  3/3 up, height 109 (spread 0), source 9c346c06b891
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 9c346c06b891, peers report ['a9a03a161427'] (last heard 4
trader    PASS  log 10.2h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9c346c06b891 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 52b1770, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 13.8h ago; 110 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 48M; repository 30.9M stored
daily     FAIL  13.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T00:19:39Z  overall FAIL  (round 49620)
nodes     PASS  3/3 up, height 109 (spread 0), source 9c346c06b891
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 9c346c06b891, peers report ['a9a03a161427'] (last heard 4
trader    PASS  log 11.3h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9c346c06b891 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 38df8f1, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.9h ago; 110 file(s) not committed
disk      PASS  126G free of 476G (73% used); logs/ 49M; repository 31.0M stored
daily     FAIL  14.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T01:27:06Z  overall FAIL  (round 49680)
nodes     PASS  3/3 up, height 109 (spread 0), source ce9f1754db0d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are ce9f1754db0d, peers report ['a9a03a161427'] (last heard 7
trader    PASS  log 12.5h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core ce9f1754db0d matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ee86b70, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 16.0h ago; 111 file(s) not committed
disk      PASS  126G free of 476G (73% used); logs/ 49M; repository 31.7M stored
daily     FAIL  16.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T02:33:07Z  overall FAIL  (round 49740)
nodes     PASS  3/3 up, height 109 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 2
trader    PASS  log 13.6h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 02dffc5, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 17.1h ago; 111 file(s) not committed
disk      PASS  126G free of 476G (73% used); logs/ 49M; repository 32.2M stored
daily     FAIL  17.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T03:41:37Z  overall FAIL  (round 49800)
nodes     PASS  3/3 up, height 109 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 2
trader    PASS  log 14.7h old; freshness exit 0: RAN: a cycle dated 2026-10-25 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD c0d5482, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 18.3h ago; 111 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 50M; repository 32.5M stored
daily     FAIL  18.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T04:47:28Z  overall FAIL  (round 49860)
nodes     PASS  3/3 up, height 109 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 1
trader    PASS  log 15.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 77cff23, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 19.4h ago; 111 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 50M; repository 33.0M stored
daily     FAIL  19.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T05:52:05Z  overall FAIL  (round 49920)
nodes     PASS  3/3 up, height 109 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 5
trader    PASS  log 16.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 77cff23, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 20.4h ago; 111 file(s) not committed
disk      PASS  128G free of 476G (72% used); logs/ 50M; repository 33.0M stored
daily     FAIL  20.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T06:56:45Z  overall FAIL  (round 49980)
nodes     PASS  3/3 up, height 109 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 3
trader    PASS  log 17.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 77cff23, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 21.5h ago; 111 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 50M; repository 33.0M stored
daily     FAIL  21.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T08:05:28Z  overall FAIL  (round 50040)
nodes     PASS  3/3 up, height 110 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 1
trader    PASS  log 19.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-25T08:31:55Z REFUSED (24h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 77cff23, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 22.7h ago; 112 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 51M; repository 33.0M stored
daily     FAIL  22.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T09:10:34Z  overall FAIL  (round 50100)
nodes     PASS  3/3 up, height 110 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 2
trader    PASS  log 20.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 77cff23, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 23.8h ago; 113 file(s) not committed
disk      PASS  127G free of 476G (73% used); logs/ 51M; repository 29.3M stored
daily     FAIL  23.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-26T10:16:39Z  overall WARN  (round 50160)
nodes     PASS  3/3 up, height 110 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 2
trader    PASS  log 21.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 77cff23, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.9h ago; 113 file(s) not committed
disk      PASS  125G free of 476G (73% used); logs/ 52M; repository 29.3M stored
daily     WARN  0.9h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T11:23:51Z  overall WARN  (round 50220)
nodes     PASS  3/3 up, height 110 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 3
trader    PASS  log 22.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 9ef98a2, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.1h ago; 114 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 52M; repository 29.5M stored
daily     WARN  2.1h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T12:31:47Z  overall WARN  (round 50280)
nodes     PASS  3/3 up, height 110 (spread 0), source 14a344ddaf42
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 14a344ddaf42, peers report ['ce9f1754db0d'] (last heard 3
trader    PASS  log 23.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 14a344ddaf42 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 879a76d, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.2h ago; 114 file(s) not committed
disk      PASS  123G free of 476G (74% used); logs/ 52M; repository 29.9M stored
daily     WARN  3.2h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T13:38:38Z  overall FAIL  (round 50340)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 8
trader    PASS  log 0.6h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 8f98863, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.3h ago; 114 file(s) not committed
disk      PASS  122G free of 476G (74% used); logs/ 51M; repository 30.9M stored
daily     WARN  4.3h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T14:47:01Z  overall FAIL  (round 50400)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 1
trader    PASS  log 1.8h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 8f98863, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.4h ago; 114 file(s) not committed
disk      PASS  119G free of 476G (74% used); logs/ 52M; repository 30.9M stored
daily     WARN  5.4h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T15:54:29Z  overall FAIL  (round 50460)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 7
trader    PASS  log 2.9h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 8f98863, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.6h ago; 115 file(s) not committed
disk      PASS  118G free of 476G (75% used); logs/ 52M; repository 30.9M stored
daily     WARN  6.6h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T17:02:14Z  overall FAIL  (round 50520)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 5
trader    PASS  log 4.0h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 3fbb07d, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.7h ago; 118 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 52M; repository 31.3M stored
daily     WARN  7.7h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T18:09:25Z  overall FAIL  (round 50580)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: anomaly SPIKE -- peer_message_error (recent 5 vs expected 1.0)
trader    PASS  log 5.2h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 1842410, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.8h ago; 115 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 53M; repository 31.5M stored
daily     WARN  8.8h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T19:17:32Z  overall FAIL  (round 50640)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 1
trader    PASS  log 6.3h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 1842410, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.0h ago; 115 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 53M; repository 31.5M stored
daily     WARN  9.9h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T20:25:10Z  overall FAIL  (round 50700)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 1
trader    PASS  log 7.4h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (12h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD c68c69b, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.1h ago; 117 file(s) not committed
disk      PASS  121G free of 476G (74% used); logs/ 54M; repository 31.7M stored
daily     WARN  11.1h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T21:32:23Z  overall FAIL  (round 50760)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 6
trader    PASS  log 8.5h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 9cbe3d5, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.2h ago; 117 file(s) not committed
disk      PASS  120G free of 476G (74% used); logs/ 54M; repository 32.0M stored
daily     WARN  12.2h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T22:39:46Z  overall FAIL  (round 50820)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 3
trader    PASS  log 9.7h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 9cbe3d5, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 13.3h ago; 117 file(s) not committed
disk      PASS  119G free of 476G (75% used); logs/ 54M; repository 32.0M stored
daily     WARN  13.3h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-26T23:47:13Z  overall FAIL  (round 50880)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 2
trader    PASS  log 10.8h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 9cbe3d5, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.4h ago; 119 file(s) not committed
disk      PASS  118G free of 476G (75% used); logs/ 54M; repository 32.0M stored
daily     WARN  14.4h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T00:56:56Z  overall FAIL  (round 50940)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 621dde1456c7, peers report ['ce9f1754db0d'] (last heard 1
trader    PASS  log 11.9h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 15.6h ago; 117 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 55M; repository 32.1M stored
daily     WARN  15.6h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T02:05:44Z  overall FAIL  (round 51000)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 13.1h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 16.8h ago; 121 file(s) not committed
disk      PASS  116G free of 476G (75% used); logs/ 55M; repository 32.1M stored
daily     WARN  16.8h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T03:13:50Z  overall FAIL  (round 51060)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 14.2h old; freshness exit 0: RAN: a cycle dated 2026-10-26 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 17.9h ago; 122 file(s) not committed
disk      PASS  116G free of 476G (75% used); logs/ 55M; repository 32.1M stored
daily     WARN  17.9h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T04:21:22Z  overall FAIL  (round 51120)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 15.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 19.0h ago; 122 file(s) not committed
disk      PASS  116G free of 476G (75% used); logs/ 56M; repository 32.1M stored
daily     WARN  19.0h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T05:29:26Z  overall FAIL  (round 51180)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 16.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 20.2h ago; 122 file(s) not committed
disk      PASS  115G free of 476G (75% used); logs/ 56M; repository 32.1M stored
daily     WARN  20.1h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T06:37:13Z  overall FAIL  (round 51240)
nodes     PASS  3/3 up, height 111 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 17.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 21.3h ago; 122 file(s) not committed
disk      PASS  115G free of 476G (75% used); logs/ 56M; repository 32.1M stored
daily     WARN  21.3h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T07:45:19Z  overall FAIL  (round 51300)
nodes     PASS  3/3 up, height 112 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 18.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-26T08:28:42Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 22.4h ago; 123 file(s) not committed
disk      PASS  114G free of 476G (76% used); logs/ 56M; repository 32.1M stored
daily     WARN  22.4h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T08:57:52Z  overall FAIL  (round 51360)
nodes     PASS  3/3 up, height 112 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 20.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (0h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD 5767cd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 23.6h ago; 125 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 51M; repository 29.5M stored
daily     WARN  23.6h ago: PC node degraded | phone node healthy | sync verified | tests UNDETERMINED | regressions PASS | new failures 5 | rolled back 0

## 2026-10-27T10:08:43Z  overall FAIL  (round 51420)
nodes     PASS  3/3 up, height 112 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 21.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 7635042, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 125 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 52M; repository 29.6M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T11:13:41Z  overall FAIL  (round 51480)
nodes     PASS  3/3 up, height 112 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 22.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 7635042, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.8h ago; 125 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 52M; repository 29.6M stored
daily     FAIL  1.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T12:18:25Z  overall FAIL  (round 51540)
nodes     PASS  3/3 up, height 112 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 23.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 7635042, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.9h ago; 125 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 52M; repository 29.6M stored
daily     FAIL  2.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T13:23:45Z  overall FAIL  (round 51600)
nodes     PASS  3/3 up, height 113 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 0.4h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 7635042, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 125 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 52M; repository 29.6M stored
daily     FAIL  4.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T14:28:44Z  overall FAIL  (round 51660)
nodes     PASS  3/3 up, height 113 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 1.5h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 7635042, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.0h ago; 125 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 53M; repository 29.6M stored
daily     FAIL  5.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T15:33:49Z  overall FAIL  (round 51720)
nodes     PASS  3/3 up, height 113 (spread 0), source 621dde1456c7
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 2.6h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core 621dde1456c7 (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at 14a344ddaf42, the core is 621dde1456c7; EXPECTED_LINES is 13523, the core has 13559 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 82b27fa, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.1h ago; 125 file(s) not committed
disk      PASS  118G free of 476G (75% used); logs/ 53M; repository 29.7M stored
daily     FAIL  6.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T16:45:56Z  overall FAIL  (round 51780)
nodes     PASS  3/3 up, height 113 (spread 0), source 0db02645f47f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 0db02645f47f, peers report ['621dde1456c7'] (last heard 5
trader    PASS  log 3.8h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 0db02645f47f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 574e52a, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.3h ago; 126 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 51M; repository 30.0M stored
daily     FAIL  7.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T18:17:29Z  overall FAIL  (round 51840)
nodes     PASS  3/3 up, height 113 (spread 0), source 0db02645f47f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 0db02645f47f, peers report ['621dde1456c7'] (last heard 2
trader    PASS  log 5.3h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 0db02645f47f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 0c9bac2, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.9h ago; 126 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 51M; repository 30.1M stored
daily     FAIL  8.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T19:49:19Z  overall FAIL  (round 51900)
nodes     PASS  3/3 up, height 113 (spread 0), source 0db02645f47f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 0db02645f47f, peers report ['621dde1456c7'] (last heard 1
trader    PASS  log 6.8h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 0db02645f47f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 1e99bf6, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.4h ago; 128 file(s) not committed
disk      PASS  114G free of 476G (76% used); logs/ 51M; repository 30.2M stored
daily     FAIL  10.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T21:04:00Z  overall FAIL  (round 51960)
nodes     PASS  3/3 up, height 113 (spread 0), source 0db02645f47f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 0db02645f47f, peers report ['621dde1456c7'] (last heard 5
trader    PASS  log 8.1h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 0db02645f47f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 1e99bf6, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.6h ago; 128 file(s) not committed
disk      PASS  113G free of 476G (76% used); logs/ 52M; repository 30.2M stored
daily     FAIL  11.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T22:08:12Z  overall FAIL  (round 52020)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 46fc4b09a63f, peers report ['621dde1456c7'] (last heard 6
trader    PASS  log 9.1h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 3ae671e, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.7h ago; 128 file(s) not committed
disk      PASS  115G free of 476G (75% used); logs/ 52M; repository 30.6M stored
daily     FAIL  12.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-27T23:12:58Z  overall FAIL  (round 52080)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 46fc4b09a63f, peers report ['621dde1456c7'] (last heard 1
trader    PASS  log 10.2h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 3ae671e, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 13.8h ago; 128 file(s) not committed
disk      PASS  116G free of 476G (75% used); logs/ 52M; repository 30.6M stored
daily     FAIL  13.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T00:17:52Z  overall FAIL  (round 52140)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 46fc4b09a63f, peers report ['621dde1456c7'] (last heard 4
trader    PASS  log 11.3h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 3ae671e, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.9h ago; 128 file(s) not committed
disk      PASS  117G free of 476G (75% used); logs/ 52M; repository 30.6M stored
daily     FAIL  14.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T01:23:28Z  overall FAIL  (round 52200)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 46fc4b09a63f, peers report ['621dde1456c7'] (last heard 2
trader    PASS  log 12.4h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 7f18cdb, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.0h ago; 128 file(s) not committed
disk      PASS  122G free of 476G (74% used); logs/ 53M; repository 31.2M stored
daily     FAIL  15.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T02:28:14Z  overall FAIL  (round 52260)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 13.5h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 7f18cdb, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.1h ago; 128 file(s) not committed
disk      PASS  122G free of 476G (74% used); logs/ 53M; repository 31.2M stored
daily     FAIL  17.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T03:33:22Z  overall FAIL  (round 52320)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 14.6h old; freshness exit 0: RAN: a cycle dated 2026-10-27 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 45a8b83, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.8h ago; 128 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 53M; repository 32.4M stored
daily     FAIL  18.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T04:38:37Z  overall FAIL  (round 52380)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 15.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 128 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 53M; repository 32.4M stored
daily     FAIL  19.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T05:43:25Z  overall FAIL  (round 52440)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 16.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.9h ago; 128 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 53M; repository 32.4M stored
daily     FAIL  20.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T06:48:34Z  overall FAIL  (round 52500)
nodes     PASS  3/3 up, height 113 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 17.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 128 file(s) not committed
disk      PASS  126G free of 476G (73% used); logs/ 54M; repository 32.4M stored
daily     FAIL  21.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T07:53:51Z  overall FAIL  (round 52560)
nodes     PASS  3/3 up, height 114 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.1137+3ae671e, and build 0.1.1139+f97d4bd is here and newer by 5.6 h -- open http://10
trader    PASS  log 18.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-27T08:30:46Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 129 file(s) not committed
disk      PASS  125G free of 476G (73% used); logs/ 54M; repository 32.4M stored
daily     FAIL  22.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T09:00:06Z  overall FAIL  (round 52620)
nodes     PASS  3/3 up, height 114 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 20.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.2h ago; 131 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 54M; repository 29.9M stored
daily     FAIL  23.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions FAIL | new failures 15 | rolled back 0

## 2026-10-28T10:06:02Z  overall FAIL  (round 52680)
nodes     PASS  3/3 up, height 114 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 21.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 132 file(s) not committed
disk      PASS  127G free of 476G (73% used); logs/ 54M; repository 29.9M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T11:11:11Z  overall FAIL  (round 52740)
nodes     PASS  3/3 up, height 114 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 22.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD dfacbe7, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.8h ago; 135 file(s) not committed
disk      PASS  127G free of 476G (73% used); logs/ 54M; repository 29.9M stored
daily     FAIL  1.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T12:16:44Z  overall FAIL  (round 52800)
nodes     PASS  3/3 up, height 114 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 23.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 8c4bcd8, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.9h ago; 132 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 55M; repository 30.7M stored
daily     FAIL  2.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T13:22:28Z  overall FAIL  (round 52860)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 0.4h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD 8c4bcd8, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 132 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 55M; repository 30.7M stored
daily     FAIL  4.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T14:27:23Z  overall FAIL  (round 52920)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 1.5h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 132 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 55M; repository 30.7M stored
daily     FAIL  5.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T15:32:29Z  overall FAIL  (round 52980)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 2.5h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.1h ago; 132 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 55M; repository 30.7M stored
daily     FAIL  6.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T16:37:53Z  overall FAIL  (round 53040)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: road_stalled is present and break_stall held -- nothing a retry can break -- waiting on their own gro
trader    PASS  log 3.6h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.2h ago; 132 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 55M; repository 30.7M stored
daily     FAIL  7.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T17:42:56Z  overall FAIL  (round 53100)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 4.7h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.3h ago; 132 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 55M; repository 30.7M stored
daily     FAIL  8.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T18:48:36Z  overall FAIL  (round 53160)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 5.8h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.4h ago; 132 file(s) not committed
disk      PASS  130G free of 476G (72% used); logs/ 56M; repository 30.7M stored
daily     FAIL  9.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T19:59:41Z  overall FAIL  (round 53220)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 7.0h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (12h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.6h ago; 133 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 56M; repository 30.7M stored
daily     FAIL  10.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T21:09:06Z  overall FAIL  (round 53280)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 8.2h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.8h ago; 133 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 56M; repository 30.7M stored
daily     FAIL  11.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T22:17:41Z  overall FAIL  (round 53340)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: moltbook_strikes is present and nothing here repairs it -- {"run": 6, "warn_at": 5, "suspends_at": 10
trader    PASS  log 9.3h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.9h ago; 133 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 57M; repository 30.7M stored
daily     FAIL  12.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-28T23:24:23Z  overall FAIL  (round 53400)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: moltbook_strikes is present and nothing here repairs it -- {"run": 6, "warn_at": 5, "suspends_at": 10
trader    PASS  log 10.4h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.0h ago; 134 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 57M; repository 30.7M stored
daily     FAIL  14.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T00:29:37Z  overall FAIL  (round 53460)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: moltbook_strikes is present and nothing here repairs it -- {"run": 6, "warn_at": 5, "suspends_at": 10
trader    PASS  log 11.5h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       PASS  HEAD f08ce10, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 15.1h ago; 134 file(s) not committed
disk      PASS  128G free of 476G (73% used); logs/ 57M; repository 30.7M stored
daily     FAIL  15.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T01:36:25Z  overall FAIL  (round 53520)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 12.6h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 811e215, 5 ahead / 0 behind origin/main as of the last fetch; last fetch 16.2h ago; 134 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 57M; repository 30.9M stored
daily     FAIL  16.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T02:45:47Z  overall FAIL  (round 53580)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 13.8h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 811e215, 5 ahead / 0 behind origin/main as of the last fetch; last fetch 17.4h ago; 134 file(s) not committed
disk      PASS  129G free of 476G (72% used); logs/ 57M; repository 30.9M stored
daily     FAIL  17.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T03:57:44Z  overall FAIL  (round 53640)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 15.0h old; freshness exit 0: RAN: a cycle dated 2026-10-28 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 811e215, 5 ahead / 0 behind origin/main as of the last fetch; last fetch 18.6h ago; 134 file(s) not committed
disk      PASS  126G free of 476G (73% used); logs/ 57M; repository 30.9M stored
daily     FAIL  18.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T05:08:28Z  overall FAIL  (round 53700)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 16.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 811e215, 5 ahead / 0 behind origin/main as of the last fetch; last fetch 19.7h ago; 134 file(s) not committed
disk      PASS  125G free of 476G (73% used); logs/ 58M; repository 30.9M stored
daily     FAIL  19.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T06:19:57Z  overall FAIL  (round 53760)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 17.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 811e215, 5 ahead / 0 behind origin/main as of the last fetch; last fetch 20.9h ago; 134 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 58M; repository 30.9M stored
daily     FAIL  20.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T07:30:37Z  overall FAIL  (round 53820)
nodes     PASS  3/3 up, height 115 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 18.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-28T08:28:31Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 811e215, 5 ahead / 0 behind origin/main as of the last fetch; last fetch 22.1h ago; 134 file(s) not committed
disk      PASS  124G free of 476G (73% used); logs/ 58M; repository 30.9M stored
daily     FAIL  22.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T08:42:08Z  overall FAIL  (round 53880)
nodes     PASS  3/3 up, height 116 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 19.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (0h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 23.3h ago; 135 file(s) not committed
disk      PASS  121G free of 476G (74% used); logs/ 58M; repository 30.1M stored
daily     FAIL  23.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T09:55:00Z  overall FAIL  (round 53940)
nodes     PASS  3/3 up, height 116 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 20.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 24.5h ago; 135 file(s) not committed
disk      PASS  118G free of 476G (75% used); logs/ 59M; repository 30.2M stored
daily     FAIL  24.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 1 | rolled back 0

## 2026-10-29T11:08:48Z  overall FAIL  (round 54000)
nodes     PASS  3/3 up, height 116 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 22.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 135 file(s) not committed
disk      PASS  115G free of 476G (75% used); logs/ 59M; repository 30.2M stored
daily     FAIL  0.7h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T12:21:44Z  overall FAIL  (round 54060)
nodes     PASS  3/3 up, height 116 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 23.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 135 file(s) not committed
disk      PASS  114G free of 476G (76% used); logs/ 59M; repository 30.2M stored
daily     FAIL  1.9h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T13:33:30Z  overall FAIL  (round 54120)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 0.6h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 3.1h ago; 135 file(s) not committed
disk      PASS  114G free of 476G (76% used); logs/ 59M; repository 30.2M stored
daily     FAIL  3.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T14:46:24Z  overall FAIL  (round 54180)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 1.8h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 4.3h ago; 135 file(s) not committed
disk      PASS  113G free of 476G (76% used); logs/ 59M; repository 30.2M stored
daily     FAIL  4.3h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T16:03:36Z  overall FAIL  (round 54240)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: phone phone: SILENT since 2026-10-29T05:23:16-0400 (last: height 116) -- the node or the app stopped, or the W
trader    PASS  log 3.1h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 5.6h ago; 135 file(s) not committed
disk      PASS  118G free of 476G (75% used); logs/ 59M; repository 30.2M stored
daily     FAIL  5.6h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T17:15:54Z  overall FAIL  (round 54300)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 4.3h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 46fc4b09a63f but MANIFEST.sha256 pins 621dde1456c7 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD 8d74252, 6 ahead / 0 behind origin/main as of the last fetch; last fetch 6.8h ago; 135 file(s) not committed
disk      PASS  118G free of 476G (75% used); logs/ 60M; repository 30.2M stored
daily     FAIL  6.8h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T18:30:03Z  overall FAIL  (round 54360)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 5.5h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD b4d9887, 7 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 134 file(s) not committed
disk      PASS  115G free of 476G (75% used); logs/ 60M; repository 30.3M stored
daily     FAIL  8.0h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T19:41:50Z  overall FAIL  (round 54420)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 6.7h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.9h ago; 134 file(s) not committed
disk      PASS  113G free of 476G (76% used); logs/ 60M; repository 30.3M stored
daily     FAIL  9.2h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T20:54:51Z  overall FAIL  (round 54480)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 7.9h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (12h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.1h ago; 134 file(s) not committed
disk      PASS  113G free of 476G (76% used); logs/ 61M; repository 30.3M stored
daily     FAIL  10.5h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T22:07:39Z  overall FAIL  (round 54540)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 9.1h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.3h ago; 134 file(s) not committed
disk      PASS  112G free of 476G (76% used); logs/ 61M; repository 30.3M stored
daily     FAIL  11.7h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-29T23:19:49Z  overall FAIL  (round 54600)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 10.3h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.5h ago; 134 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 61M; repository 30.3M stored
daily     FAIL  12.9h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T00:36:13Z  overall FAIL  (round 54660)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 11.6h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.8h ago; 134 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 61M; repository 30.3M stored
daily     FAIL  14.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T01:48:18Z  overall FAIL  (round 54720)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 12.8h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.0h ago; 134 file(s) not committed
disk      PASS  108G free of 476G (77% used); logs/ 61M; repository 30.3M stored
daily     FAIL  15.3h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T03:01:18Z  overall FAIL  (round 54780)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 14.0h old; freshness exit 0: RAN: a cycle dated 2026-10-29 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.2h ago; 135 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 61M; repository 30.3M stored
daily     FAIL  16.6h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T04:14:05Z  overall FAIL  (round 54840)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 15.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD b4d9887, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.4h ago; 148 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 61M; repository 30.3M stored
daily     FAIL  17.8h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T05:26:33Z  overall FAIL  (round 54900)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 16.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ac35ad3, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.6h ago; 138 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 59M; repository 30.6M stored
daily     FAIL  19.0h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T06:33:19Z  overall FAIL  (round 54960)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 17.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ac35ad3, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.7h ago; 138 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 59M; repository 30.6M stored
daily     FAIL  20.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T07:40:34Z  overall FAIL  (round 55020)
nodes     PASS  3/3 up, height 117 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 18.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-29T08:30:26Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ac35ad3, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 12.8h ago; 138 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 59M; repository 30.6M stored
daily     FAIL  21.2h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T08:50:44Z  overall FAIL  (round 55080)
nodes     PASS  3/3 up, height 118 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 19.8h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (0h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD ac35ad3, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.0h ago; 140 file(s) not committed
disk      PASS  108G free of 476G (77% used); logs/ 60M; repository 30.1M stored
daily     FAIL  22.4h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions FAIL | new failures 1 | rolled back 0

## 2026-10-30T10:05:03Z  overall FAIL  (round 55140)
nodes     PASS  3/3 up, height 118 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 21.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e441ee5, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 142 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 60M; repository 30.6M stored
daily     FAIL  0.7h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T11:14:45Z  overall FAIL  (round 55200)
nodes     PASS  3/3 up, height 118 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 22.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 55c8a43, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 140 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 60M; repository 30.7M stored
daily     FAIL  1.9h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T12:24:22Z  overall FAIL  (round 55260)
nodes     PASS  3/3 up, height 118 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 23.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 55c8a43, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.1h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 60M; repository 30.7M stored
daily     FAIL  3.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T13:35:15Z  overall FAIL  (round 55320)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 0.6h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 55c8a43, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.3h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 60M; repository 30.7M stored
daily     FAIL  4.2h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T14:48:59Z  overall FAIL  (round 55380)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 1.8h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 55c8a43, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.5h ago; 146 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 61M; repository 30.7M stored
daily     FAIL  5.5h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T16:05:50Z  overall FAIL  (round 55440)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 3.1h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 0f1cba0, 8 ahead / 0 behind origin/main as of the last fetch; last fetch 6.8h ago; 144 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 60M; repository 31.9M stored
daily     FAIL  6.7h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T17:20:07Z  overall FAIL  (round 55500)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 4.3h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD cf9ac3e, 10 ahead / 0 behind origin/main as of the last fetch; last fetch 8.0h ago; 142 file(s) not committed
disk      PASS  110G free of 476G (76% used); logs/ 61M; repository 32.0M stored
daily     FAIL  8.0h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T18:33:01Z  overall FAIL  (round 55560)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 5.5h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD cf9ac3e, 10 ahead / 0 behind origin/main as of the last fetch; last fetch 9.2h ago; 142 file(s) not committed
disk      PASS  111G free of 476G (76% used); logs/ 61M; repository 32.0M stored
daily     FAIL  9.2h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T19:47:40Z  overall FAIL  (round 55620)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 6.8h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD cf9ac3e, 10 ahead / 0 behind origin/main as of the last fetch; last fetch 10.5h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 61M; repository 32.0M stored
daily     FAIL  10.4h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T21:11:49Z  overall FAIL  (round 55680)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 8.2h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 55b8e90, 11 ahead / 0 behind origin/main as of the last fetch; last fetch 11.9h ago; 158 file(s) not committed
disk      PASS  107G free of 476G (77% used); logs/ 61M; repository 32.2M stored
daily     FAIL  11.8h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T22:29:08Z  overall FAIL  (round 55740)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 9.5h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 55b8e90, 11 ahead / 0 behind origin/main as of the last fetch; last fetch 13.2h ago; 167 file(s) not committed
disk      PASS  105G free of 476G (77% used); logs/ 62M; repository 32.2M stored
daily     FAIL  13.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-30T23:43:24Z  overall FAIL  (round 55800)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 10.7h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 97b676b, 12 ahead / 0 behind origin/main as of the last fetch; last fetch 14.4h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 57M; repository 33.2M stored
daily     FAIL  14.4h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T00:57:31Z  overall FAIL  (round 55860)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 12.0h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 943b809, 14 ahead / 0 behind origin/main as of the last fetch; last fetch 15.6h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 57M; repository 34.0M stored
daily     FAIL  15.6h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T02:10:44Z  overall FAIL  (round 55920)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 13.2h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 943b809, 14 ahead / 0 behind origin/main as of the last fetch; last fetch 16.8h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 58M; repository 34.0M stored
daily     FAIL  16.8h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T03:24:35Z  overall FAIL  (round 55980)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 14.4h old; freshness exit 0: RAN: a cycle dated 2026-10-30 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 943b809, 14 ahead / 0 behind origin/main as of the last fetch; last fetch 18.1h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 58M; repository 34.0M stored
daily     FAIL  18.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T04:40:15Z  overall FAIL  (round 56040)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 15.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 943b809, 14 ahead / 0 behind origin/main as of the last fetch; last fetch 19.3h ago; 142 file(s) not committed
disk      PASS  108G free of 476G (77% used); logs/ 58M; repository 34.0M stored
daily     FAIL  19.3h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T05:55:31Z  overall FAIL  (round 56100)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 16.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 25accf8, 15 ahead / 0 behind origin/main as of the last fetch; last fetch 20.6h ago; 142 file(s) not committed
disk      PASS  109G free of 476G (77% used); logs/ 58M; repository 34.7M stored
daily     FAIL  20.6h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T07:13:32Z  overall FAIL  (round 56160)
nodes     PASS  3/3 up, height 119 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 18.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 25accf8, 15 ahead / 0 behind origin/main as of the last fetch; last fetch 21.9h ago; 142 file(s) not committed
disk      PASS  107G free of 476G (77% used); logs/ 58M; repository 34.7M stored
daily     FAIL  21.9h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T08:28:32Z  overall FAIL  (round 56220)
nodes     PASS  3/3 up, height 120 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 19.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-30T08:35:05Z REFUSED (24h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 25accf8, 15 ahead / 0 behind origin/main as of the last fetch; last fetch 23.1h ago; 143 file(s) not committed
disk      PASS  106G free of 476G (77% used); logs/ 59M; repository 30.3M stored
daily     FAIL  23.1h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T09:42:58Z  overall FAIL  (round 56280)
nodes     PASS  3/3 up, height 120 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 20.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 25accf8, 15 ahead / 0 behind origin/main as of the last fetch; last fetch 24.4h ago; 143 file(s) not committed
disk      PASS  106G free of 476G (77% used); logs/ 59M; repository 30.3M stored
daily     FAIL  24.4h ago: PC node degraded | phone node degraded | sync unverified | tests FAIL | regressions PASS | new failures 6 | rolled back 0

## 2026-10-31T10:58:34Z  overall FAIL  (round 56340)
nodes     PASS  3/3 up, height 120 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 22.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 25accf8, 15 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 148 file(s) not committed
disk      PASS  105G free of 476G (77% used); logs/ 59M; repository 30.3M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T12:16:04Z  overall FAIL  (round 56400)
nodes     PASS  3/3 up, height 120 (spread 0), source 46fc4b09a63f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 23.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 46fc4b09a63f matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 0cd6dfe, 16 ahead / 0 behind origin/main as of the last fetch; last fetch 2.0h ago; 145 file(s) not committed
disk      PASS  104G free of 476G (78% used); logs/ 60M; repository 31.0M stored
daily     FAIL  2.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T13:32:12Z  overall FAIL  (round 56460)
nodes     PASS  3/3 up, height 121 (spread 0), source 81daffbb9434
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 81daffbb9434, peers report ['46fc4b09a63f'] (last heard 2
trader    PASS  log 0.5h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 81daffbb9434 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD d0e55b5, 17 ahead / 0 behind origin/main as of the last fetch; last fetch 3.3h ago; 145 file(s) not committed
disk      PASS  103G free of 476G (78% used); logs/ 59M; repository 32.2M stored
daily     FAIL  3.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T14:49:45Z  overall FAIL  (round 56520)
nodes     PASS  3/3 up, height 121 (spread 0), source 81daffbb9434
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 81daffbb9434, peers report ['46fc4b09a63f'] (last heard 3
trader    PASS  log 1.8h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 81daffbb9434 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 4bb5562, 18 ahead / 0 behind origin/main as of the last fetch; last fetch 4.6h ago; 146 file(s) not committed
disk      PASS  148G free of 476G (68% used); logs/ 60M; repository 32.9M stored
daily     FAIL  4.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T15:59:57Z  overall FAIL  (round 56580)
nodes     PASS  3/3 up, height 121 (spread 0), source 81daffbb9434
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 81daffbb9434, peers report ['46fc4b09a63f'] (last heard 3
trader    PASS  log 3.0h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 81daffbb9434 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 16979fd, 21 ahead / 0 behind origin/main as of the last fetch; last fetch 5.7h ago; 146 file(s) not committed
disk      PASS  147G free of 476G (69% used); logs/ 60M; repository 33.7M stored
daily     FAIL  5.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T17:09:29Z  overall FAIL  (round 56640)
nodes     PASS  3/3 up, height 121 (spread 0), source 81daffbb9434
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: mesh is running more than one source: we are 81daffbb9434, peers report ['46fc4b09a63f'] (last heard 1
trader    PASS  log 4.2h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 81daffbb9434 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD dcecc56, 23 ahead / 0 behind origin/main as of the last fetch; last fetch 6.9h ago; 146 file(s) not committed
disk      PASS  147G free of 476G (69% used); logs/ 60M; repository 33.9M stored
daily     FAIL  6.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T18:21:04Z  overall FAIL  (round 56700)
nodes     WARN  3/3 up, height 121 (spread 0), source 81daffbb9434/f3af9bf03281
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are 81daffbb9434, peers report ['46fc4b09a63f'] (last heard 7
trader    PASS  log 5.3h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      FAIL  core on disk 6f890c4c335c but MANIFEST.sha256 pins 81daffbb9434 -- an old copy, a partial copy or a hand edit. Re-pin in the SAME change as the file
git       WARN  HEAD dcecc56, 23 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 157 file(s) not committed
disk      PASS  147G free of 476G (69% used); logs/ 60M; repository 33.9M stored
daily     FAIL  8.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T19:33:48Z  overall FAIL  (round 56760)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 6f890c4c335c, peers report ['46fc4b09a63f'] (last heard 5
trader    PASS  log 6.6h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 1671d52, 25 ahead / 0 behind origin/main as of the last fetch; last fetch 9.3h ago; 146 file(s) not committed
disk      PASS  149G free of 476G (68% used); logs/ 61M; repository 35.8M stored
daily     FAIL  9.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T20:48:29Z  overall FAIL  (round 56820)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 6f890c4c335c, peers report ['46fc4b09a63f'] (last heard 3
trader    PASS  log 7.8h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (12h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD edc3368, 27 ahead / 0 behind origin/main as of the last fetch; last fetch 10.6h ago; 146 file(s) not committed
disk      PASS  148G free of 476G (68% used); logs/ 61M; repository 36.0M stored
daily     FAIL  10.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T22:01:42Z  overall FAIL  (round 56880)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=3, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 9.0h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 0f8d997, 28 ahead / 0 behind origin/main as of the last fetch; last fetch 11.8h ago; 146 file(s) not committed
disk      PASS  148G free of 476G (68% used); logs/ 61M; repository 36.6M stored
daily     FAIL  11.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-31T23:14:18Z  overall FAIL  (round 56940)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=3, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 10.2h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 15d4cf7, 29 ahead / 0 behind origin/main as of the last fetch; last fetch 13.0h ago; 146 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 62M; repository 36.7M stored
daily     FAIL  13.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T00:27:18Z  overall FAIL  (round 57000)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=3, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 11.5h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 1ac1587, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.1h ago; 149 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 62M; repository 38.4M stored
daily     FAIL  14.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T01:39:40Z  overall FAIL  (round 57060)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=3, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 12.7h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD a7d4fef, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.4h ago; 146 file(s) not committed
disk      PASS  152G free of 476G (68% used); logs/ 62M; repository 39.1M stored
daily     FAIL  15.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T02:52:48Z  overall FAIL  (round 57120)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=3, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 13.9h old; freshness exit 0: RAN: a cycle dated 2026-10-31 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 35c3e85, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.6h ago; 150 file(s) not committed
disk      PASS  151G free of 476G (68% used); logs/ 62M; repository 40.5M stored
daily     FAIL  16.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T04:05:02Z  overall FAIL  (round 57180)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 15.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 750fffd, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 0.3h ago; 146 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 63M; repository 44.3M stored
daily     FAIL  17.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T05:18:56Z  overall FAIL  (round 57240)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 16.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 750fffd, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.5h ago; 147 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 63M; repository 44.3M stored
daily     FAIL  19.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T06:29:45Z  overall FAIL  (round 57300)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 17.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 750fffd, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.7h ago; 147 file(s) not committed
disk      PASS  150G free of 476G (68% used); logs/ 63M; repository 44.3M stored
daily     FAIL  20.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T07:42:33Z  overall FAIL  (round 57360)
nodes     PASS  3/3 up, height 121 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 18.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-31T08:30:38Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 750fffd, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.9h ago; 147 file(s) not committed
disk      PASS  151G free of 476G (68% used); logs/ 63M; repository 44.3M stored
daily     FAIL  21.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T08:53:06Z  overall FAIL  (round 57420)
nodes     PASS  3/3 up, height 122 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 19.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (0h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 750fffd, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 149 file(s) not committed
disk      PASS  152G free of 476G (67% used); logs/ 63M; repository 31.1M stored
daily     FAIL  22.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-11-01T10:04:16Z  overall FAIL  (round 57480)
nodes     PASS  3/3 up, height 122 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  9 live -- first: node A: UNEXPECTED PEER peer_<tailnet-ip>_5081 at <tailnet-ip>:5081 -- not in this node's configured peer set 
trader    PASS  log 21.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 750fffd, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 149 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 63M; repository 31.1M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T11:11:56Z  overall FAIL  (round 57540)
nodes     PASS  3/3 up, height 122 (spread 0), source 6f890c4c335c
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: model_drift is present and nothing here repairs it -- {"drifted": ["fallback_model_2.json"], "missing
trader    PASS  log 22.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 6f890c4c335c matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD d71ea14, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 150 file(s) not committed
disk      PASS  156G free of 476G (67% used); logs/ 62M; repository 32.6M stored
daily     FAIL  1.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T12:23:50Z  overall FAIL  (round 57600)
nodes     PASS  3/3 up, height 122 (spread 0), source fb9976f93635
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are fb9976f93635, peers report ['6f890c4c335c'] (last heard 4
trader    PASS  log 23.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 3e079137ab67 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 4d5665a, 3 ahead / 0 behind origin/main as of the last fetch; last fetch 3.1h ago; 151 file(s) not committed
disk      PASS  153G free of 476G (67% used); logs/ 63M; repository 34.4M stored
daily     FAIL  3.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T13:33:47Z  overall FAIL  (round 57660)
nodes     PASS  3/3 up, height 122 (spread 0), source 3e079137ab67
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 3e079137ab67, peers report ['6f890c4c335c'] (last heard 2
trader    PASS  log 24.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 3e079137ab67 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD d31ccd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 4.2h ago; 150 file(s) not committed
disk      PASS  159G free of 476G (66% used); logs/ 63M; repository 35.1M stored
daily     FAIL  4.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T14:44:34Z  overall FAIL  (round 57720)
nodes     PASS  3/3 up, height 123 (spread 0), source 3e079137ab67
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 3e079137ab67, peers report ['6f890c4c335c'] (last heard 1
trader    PASS  log 0.7h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 3e079137ab67 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD d31ccd3, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 5.4h ago; 150 file(s) not committed
disk      PASS  159G free of 476G (66% used); logs/ 63M; repository 35.1M stored
daily     FAIL  5.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T15:54:04Z  overall FAIL  (round 57780)
nodes     FAIL  ['A'] unreachable; 2/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node B: restarted since the last check (uptime went backwards)
trader    PASS  log 1.9h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (7h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 1b52726, 3 ahead / 0 behind origin/main as of the last fetch; last fetch 6.6h ago; 149 file(s) not committed
disk      PASS  164G free of 476G (65% used); logs/ 63M; repository 36.3M stored
daily     FAIL  6.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T17:04:22Z  overall FAIL  (round 57840)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 3.1h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 23f9a57, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.1h ago; 149 file(s) not committed
disk      PASS  164G free of 476G (65% used); logs/ 63M; repository 37.0M stored
daily     FAIL  7.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T18:15:08Z  overall FAIL  (round 57900)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 4.3h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 23f9a57, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.3h ago; 149 file(s) not committed
disk      PASS  164G free of 476G (65% used); logs/ 64M; repository 37.0M stored
daily     FAIL  8.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T19:25:51Z  overall FAIL  (round 57960)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 5.4h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 23f9a57, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.4h ago; 149 file(s) not committed
disk      PASS  168G free of 476G (64% used); logs/ 64M; repository 37.0M stored
daily     FAIL  10.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T20:39:00Z  overall FAIL  (round 58020)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 6.6h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (12h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 23f9a57, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.7h ago; 149 file(s) not committed
disk      PASS  167G free of 476G (64% used); logs/ 64M; repository 37.0M stored
daily     FAIL  11.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T21:49:27Z  overall FAIL  (round 58080)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 7.8h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD 23f9a57, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.8h ago; 149 file(s) not committed
disk      PASS  169G free of 476G (64% used); logs/ 65M; repository 37.1M stored
daily     FAIL  12.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-01T22:59:21Z  overall FAIL  (round 58140)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 9.0h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       PASS  HEAD e9268d4, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.2h ago; 149 file(s) not committed
disk      PASS  169G free of 476G (64% used); logs/ 65M; repository 39.2M stored
daily     FAIL  13.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T00:08:15Z  overall FAIL  (round 58200)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 10.1h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 1.4h ago; 149 file(s) not committed
disk      PASS  169G free of 476G (64% used); logs/ 65M; repository 39.6M stored
daily     FAIL  14.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T01:18:05Z  overall FAIL  (round 58260)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 11.3h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (17h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 2.5h ago; 149 file(s) not committed
disk      PASS  170G free of 476G (64% used); logs/ 66M; repository 39.7M stored
daily     FAIL  15.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T02:28:14Z  overall FAIL  (round 58320)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  9 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 12.5h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 3.7h ago; 149 file(s) not committed
disk      PASS  170G free of 476G (64% used); logs/ 66M; repository 39.7M stored
daily     FAIL  17.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T03:43:43Z  overall FAIL  (round 58380)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  10 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 13.7h old; freshness exit 0: RAN: a cycle dated 2026-11-01 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 5.0h ago; 149 file(s) not committed
disk      PASS  169G free of 476G (64% used); logs/ 66M; repository 39.7M stored
daily     FAIL  18.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T05:01:01Z  overall FAIL  (round 58440)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 15.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 6.3h ago; 149 file(s) not committed
disk      PASS  171G free of 476G (64% used); logs/ 66M; repository 39.7M stored
daily     FAIL  19.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T06:14:54Z  overall FAIL  (round 58500)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  8 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 16.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 7.5h ago; 149 file(s) not committed
disk      PASS  170G free of 476G (64% used); logs/ 66M; repository 39.7M stored
daily     FAIL  20.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T07:27:48Z  overall FAIL  (round 58560)
nodes     PASS  3/3 up, height 123 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 3
trader    PASS  log 17.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-01T08:32:07Z REFUSED (23h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 8.7h ago; 149 file(s) not committed
disk      PASS  169G free of 476G (64% used); logs/ 67M; repository 39.7M stored
daily     FAIL  22.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T08:43:04Z  overall FAIL  (round 58620)
nodes     PASS  3/3 up, height 124 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  9 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 18.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (0h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 10.0h ago; 151 file(s) not committed
disk      PASS  172G free of 476G (63% used); logs/ 67M; repository 30.5M stored
daily     FAIL  23.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T09:57:48Z  overall FAIL  (round 58680)
nodes     PASS  3/3 up, height 124 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  9 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 20.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 11.2h ago; 151 file(s) not committed
disk      PASS  170G free of 476G (64% used); logs/ 67M; repository 31.0M stored
daily     FAIL  24.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T11:12:28Z  overall FAIL  (round 58740)
nodes     PASS  3/3 up, height 124 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  9 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 21.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (3h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 12.5h ago; 151 file(s) not committed
disk      PASS  168G free of 476G (64% used); logs/ 67M; repository 31.1M stored
daily     FAIL  25.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T12:23:59Z  overall FAIL  (round 58800)
nodes     PASS  3/3 up, height 124 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 5
trader    PASS  log 22.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (4h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 13.6h ago; 151 file(s) not committed
disk      PASS  168G free of 476G (64% used); logs/ 67M; repository 31.1M stored
daily     FAIL  27.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T13:34:00Z  overall FAIL  (round 58860)
nodes     PASS  3/3 up, height 124 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 5
trader    PASS  log 23.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (5h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 14.8h ago; 151 file(s) not committed
disk      PASS  167G free of 476G (64% used); logs/ 68M; repository 31.1M stored
daily     FAIL  28.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T14:49:42Z  overall FAIL  (round 58920)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 3
trader    PASS  log 0.8h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (6h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 16.1h ago; 151 file(s) not committed
disk      PASS  170G free of 476G (64% used); logs/ 68M; repository 31.2M stored
daily     FAIL  29.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T16:02:51Z  overall FAIL  (round 58980)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: 2 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 2.0h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (8h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 17.3h ago; 151 file(s) not committed
disk      PASS  168G free of 476G (64% used); logs/ 68M; repository 31.2M stored
daily     FAIL  the newest daily record is 30.7h old -- the daily cycle did not run: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 5 | rolled back 0

## 2026-11-02T17:18:16Z  overall FAIL  (round 59040)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: 2 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 3.3h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (9h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 151 file(s) not committed
disk      PASS  165G free of 476G (65% used); logs/ 68M; repository 31.2M stored
daily     FAIL  0.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-02T18:31:44Z  overall FAIL  (round 59100)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 9
trader    PASS  log 4.5h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (10h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 1.9h ago; 151 file(s) not committed
disk      PASS  164G free of 476G (65% used); logs/ 69M; repository 31.2M stored
daily     FAIL  1.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-02T19:50:33Z  overall FAIL  (round 59160)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 2
trader    PASS  log 5.8h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (11h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 3.2h ago; 151 file(s) not committed
disk      PASS  163G free of 476G (65% used); logs/ 64M; repository 32.7M stored
daily     FAIL  3.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-02T21:04:49Z  overall FAIL  (round 59220)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 5
trader    PASS  log 7.1h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (13h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 4.5h ago; 151 file(s) not committed
disk      PASS  161G free of 476G (66% used); logs/ 64M; repository 33.3M stored
daily     FAIL  4.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-02T22:20:38Z  overall FAIL  (round 59280)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 3
trader    PASS  log 8.3h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (14h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 5.7h ago; 151 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 64M; repository 33.7M stored
daily     FAIL  5.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-02T23:33:23Z  overall FAIL  (round 59340)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 7
trader    PASS  log 9.6h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (15h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 6.9h ago; 151 file(s) not committed
disk      PASS  157G free of 476G (67% used); logs/ 64M; repository 36.4M stored
daily     FAIL  6.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T00:46:07Z  overall FAIL  (round 59400)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 3
trader    PASS  log 10.8h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (16h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 151 file(s) not committed
disk      PASS  156G free of 476G (67% used); logs/ 64M; repository 37.3M stored
daily     FAIL  8.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T01:58:42Z  overall FAIL  (round 59460)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 3
trader    PASS  log 12.0h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (18h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 9.4h ago; 151 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 65M; repository 37.3M stored
daily     FAIL  9.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T03:11:32Z  overall FAIL  (round 59520)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 8
trader    PASS  log 13.2h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (19h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 10.6h ago; 151 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 65M; repository 37.3M stored
daily     FAIL  10.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T04:26:46Z  overall FAIL  (round 59580)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 4
trader    PASS  log 14.4h old; freshness exit 0: RAN: a cycle dated 2026-11-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (20h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 11.8h ago; 151 file(s) not committed
disk      PASS  154G free of 476G (67% used); logs/ 65M; repository 37.3M stored
daily     FAIL  11.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T05:39:40Z  overall FAIL  (round 59640)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 9
trader    PASS  log 15.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (21h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 13.0h ago; 151 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 65M; repository 37.3M stored
daily     FAIL  13.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T06:52:22Z  overall FAIL  (round 59700)
nodes     PASS  3/3 up, height 125 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 1
trader    PASS  log 16.9h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (22h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 14.3h ago; 151 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 65M; repository 37.3M stored
daily     FAIL  14.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T08:03:53Z  overall FAIL  (round 59760)
nodes     PASS  3/3 up, height 126 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 1
trader    PASS  log 18.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-02T08:26:26Z REFUSED (24h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 15.4h ago; 152 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 65M; repository 37.3M stored
daily     FAIL  15.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T09:19:53Z  overall FAIL  (round 59820)
nodes     PASS  3/3 up, height 126 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are 9114e9d5c9f5, peers report ['6f890c4c335c'] (last heard 1
trader    PASS  log 19.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-03T08:25:34Z REFUSED (1h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 0 behind origin/main as of the last fetch; last fetch 16.7h ago; 153 file(s) not committed
disk      PASS  158G free of 476G (66% used); logs/ 66M; repository 31.1M stored
daily     FAIL  16.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0

## 2026-11-03T10:39:06Z  overall FAIL  (round 59880)
nodes     PASS  3/3 up, height 126 (spread 0), source 9114e9d5c9f5
mycelium  PASS  3/3 reporting; links held: A=4, B=2, C=1
judge     PASS  baseline digest student@f245e907614, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off
trader    PASS  log 20.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-11-03T08:25:34Z REFUSED (2h ago); run-without 3/5 met, exam streak 0; unmet: exam_met_streak, own_traffic_hold_max
repo      PASS  core 9114e9d5c9f5 matches MANIFEST.sha256 and every pin, companion, version and line count verify_deploy.py checks. A substitution that rewrote both records would read clean here
git       WARN  HEAD 593ab17, 4 ahead / 10 behind origin/main as of the last fetch; last fetch 18.0h ago; 153 file(s) not committed
disk      PASS  156G free of 476G (67% used); logs/ 66M; repository 32.1M stored
daily     FAIL  18.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 3 | rolled back 0


# covenant self-evaluation ledger
# For Misha, and all that were lost to injustice.
# One block per evaluation: PASS/WARN/FAIL per layer, worst wins.
# Written by covenant_watchdog.py (report-only) and by the scheduled
# covenant-self-eval task. Append-only; rotates to .prev at 512KB.

## 2026-10-02T04:01:04Z  overall FAIL  (round 19500)
nodes     PASS  3/3 up, height 60 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@adb6c35c0c1, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 15.0h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-01T08:06:35Z PROMOTED (20h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 19.0h ago; 21 file(s) not committed
disk      PASS  292G free of 476G (38% used); logs/ 36M
daily     FAIL  19.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T05:05:07Z  overall FAIL  (round 19560)
nodes     PASS  3/3 up, height 60 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@adb6c35c0c1, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 16.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-01T08:06:35Z PROMOTED (21h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 20.0h ago; 22 file(s) not committed
disk      PASS  292G free of 476G (38% used); logs/ 36M
daily     FAIL  20.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T06:09:04Z  overall FAIL  (round 19620)
nodes     PASS  3/3 up, height 60 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@adb6c35c0c1, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 17.1h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-01T08:06:35Z PROMOTED (22h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 21.1h ago; 22 file(s) not committed
disk      PASS  289G free of 476G (39% used); logs/ 36M
daily     FAIL  21.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T07:13:10Z  overall FAIL  (round 19680)
nodes     PASS  3/3 up, height 60 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@adb6c35c0c1, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 18.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-01T08:06:35Z PROMOTED (23h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 22.2h ago; 22 file(s) not committed
disk      PASS  289G free of 476G (39% used); logs/ 36M
daily     FAIL  22.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T08:17:18Z  overall FAIL  (round 19740)
nodes     PASS  3/3 up, height 61 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 19.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (0h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 23.2h ago; 25 file(s) not committed
disk      PASS  289G free of 476G (39% used); logs/ 37M
daily     FAIL  23.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T09:21:37Z  overall FAIL  (round 19800)
nodes     PASS  3/3 up, height 61 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 20.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (1h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 24.3h ago; 25 file(s) not committed
disk      PASS  288G free of 476G (39% used); logs/ 37M
daily     FAIL  24.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T10:25:54Z  overall FAIL  (round 19860)
nodes     PASS  3/3 up, height 61 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 21.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (2h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.8h ago; 25 file(s) not committed
disk      PASS  288G free of 476G (39% used); logs/ 37M
daily     FAIL  0.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T11:30:13Z  overall FAIL  (round 19920)
nodes     PASS  3/3 up, height 61 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    PASS  log 22.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (3h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.8h ago; 25 file(s) not committed
disk      PASS  288G free of 476G (39% used); logs/ 37M
daily     FAIL  1.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T12:34:34Z  overall FAIL  (round 19980)
nodes     PASS  3/3 up, height 61 (spread 0), source b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: highway: public_ci_red is present and nothing here repairs it -- {"repo": "LAWLESS1987/covenant", "newest": {"
trader    PASS  log 23.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (4h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.9h ago; 25 file(s) not committed
disk      PASS  288G free of 476G (39% used); logs/ 37M
daily     FAIL  2.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T13:38:41Z  overall FAIL  (round 20040)
nodes     WARN  3/3 up, height 62 (spread 60), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 6
trader    PASS  log 0.6h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (5h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.0h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 37M
daily     FAIL  4.0h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T14:45:47Z  overall FAIL  (round 20100)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 6
trader    PASS  log 1.8h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (7h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.1h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 38M
daily     FAIL  5.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T15:53:59Z  overall FAIL  (round 20160)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 1
trader    PASS  log 2.9h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (8h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 6.2h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 38M
daily     FAIL  6.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T17:02:10Z  overall FAIL  (round 20220)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 2
trader    PASS  log 4.0h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (9h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.4h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 38M
daily     FAIL  7.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T18:10:19Z  overall FAIL  (round 20280)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 3
trader    PASS  log 5.2h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (10h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.5h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 38M
daily     FAIL  8.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T19:18:46Z  overall FAIL  (round 20340)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 6
trader    PASS  log 6.3h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (11h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.6h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 39M
daily     FAIL  9.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T20:26:59Z  overall FAIL  (round 20400)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 7
trader    PASS  log 7.4h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (12h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 10.8h ago; 25 file(s) not committed
disk      PASS  287G free of 476G (39% used); logs/ 39M
daily     FAIL  10.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T21:35:11Z  overall FAIL  (round 20460)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 9
trader    PASS  log 8.6h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (13h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 11.9h ago; 25 file(s) not committed
disk      PASS  277G free of 476G (41% used); logs/ 39M
daily     FAIL  11.9h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T22:43:19Z  overall FAIL  (round 20520)
nodes     FAIL  ['C'] unreachable; 2/3 up, height 62 (spread 1), source b708204ff11b/bae777a26192
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    FAIL  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['bae777a26192'] (last heard 9
trader    PASS  log 9.7h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (15h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 13.1h ago; 25 file(s) not committed
disk      PASS  277G free of 476G (41% used); logs/ 40M
daily     FAIL  13.1h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-02T23:49:49Z  overall FAIL  (round 20580)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 2
trader    PASS  log 10.8h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (16h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 14.2h ago; 25 file(s) not committed
disk      PASS  279G free of 476G (41% used); logs/ 40M
daily     FAIL  14.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T00:53:58Z  overall FAIL  (round 20640)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 3
trader    PASS  log 11.9h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (17h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 15.2h ago; 25 file(s) not committed
disk      PASS  297G free of 476G (37% used); logs/ 40M
daily     FAIL  15.2h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T01:58:52Z  overall FAIL  (round 20700)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 1
trader    PASS  log 13.0h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (18h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 16.3h ago; 25 file(s) not committed
disk      PASS  296G free of 476G (37% used); logs/ 40M
daily     FAIL  16.3h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T03:04:43Z  overall FAIL  (round 20760)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 4
trader    PASS  log 14.1h old; freshness exit 0: RAN: a cycle dated 2026-10-02 COMPLETED -- the trader printed it, not the launcher.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (19h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 17.4h ago; 25 file(s) not committed
disk      PASS  296G free of 476G (37% used); logs/ 41M
daily     FAIL  17.4h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T04:10:37Z  overall FAIL  (round 20820)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 7
trader    PASS  log 15.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (20h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 18.5h ago; 25 file(s) not committed
disk      PASS  295G free of 476G (37% used); logs/ 41M
daily     FAIL  18.5h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T05:15:03Z  overall FAIL  (round 20880)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 2
trader    PASS  log 16.2h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (21h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 19.6h ago; 25 file(s) not committed
disk      PASS  295G free of 476G (37% used); logs/ 41M
daily     FAIL  19.6h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T06:19:02Z  overall FAIL  (round 20940)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 2
trader    PASS  log 17.3h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (22h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 20.7h ago; 25 file(s) not committed
disk      PASS  295G free of 476G (38% used); logs/ 41M
daily     FAIL  20.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T07:22:59Z  overall FAIL  (round 21000)
nodes     WARN  3/3 up, height 62 (spread 61), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@ab482e6d6ad, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 2
trader    PASS  log 18.4h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-02T08:11:23Z PROMOTED (23h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 21.7h ago; 25 file(s) not committed
disk      PASS  295G free of 476G (38% used); logs/ 41M
daily     FAIL  21.7h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T08:27:07Z  overall FAIL  (round 21060)
nodes     WARN  3/3 up, height 63 (spread 62), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@26569e1824d, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 3
trader    PASS  log 19.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-03T08:05:44Z PROMOTED (0h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 22.8h ago; 28 file(s) not committed
disk      PASS  294G free of 476G (38% used); logs/ 42M
daily     FAIL  22.8h ago: PC node degraded | phone node healthy | sync verified | tests FAIL | regressions PASS | new failures 0 | rolled back 0

## 2026-10-03T09:31:08Z  overall FAIL  (round 21120)
nodes     WARN  3/3 up, height 63 (spread 62), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@26569e1824d, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 3
trader    PASS  log 20.5h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-03T08:05:44Z PROMOTED (1h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       PASS  HEAD 36344c9, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 0.7h ago; 28 file(s) not committed
disk      PASS  298G free of 476G (37% used); logs/ 42M
daily     FAIL  0.7h ago: PC node failed | phone node healthy | sync failed | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-03T10:35:10Z  overall FAIL  (round 21180)
nodes     WARN  3/3 up, height 63 (spread 62), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@26569e1824d, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 3
trader    PASS  log 21.6h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-03T08:05:44Z PROMOTED (2h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD e635ad9, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 0.3h ago; 12 file(s) not committed
disk      PASS  298G free of 476G (37% used); logs/ 42M
daily     FAIL  1.8h ago: PC node failed | phone node healthy | sync failed | tests FAIL | regressions FAIL | new failures 10 | rolled back 0

## 2026-10-03T11:39:39Z  overall FAIL  (round 21240)
nodes     WARN  3/3 up, height 63 (spread 62), source 315371e53709/b708204ff11b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@26569e1824d, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: mesh is running more than one source: we are b708204ff11b, peers report ['315371e53709'] (last heard 1
trader    PASS  log 22.7h old; freshness exit 0: NOT YET DUE: trigger 09:00 plus 5 min grace has not passed.
student   PASS  last cycle 2026-10-03T08:05:44Z PROMOTED (4h ago); run-without 2/5 met, exam streak 0; unmet: exam_met_streak, panel_coverage_min, own_traffic_hold_max
repo      FAIL  core b708204ff11b (v8.40) matches MANIFEST.sha256, but verify_deploy.py disagrees with the tree: it pins the core at e8a79ee502d8, the core is b708204ff11b; EXPECTED_LINES is 12783, the core has 12799 lines (checked after a restart) -- stale pins (M53) or a changed file; verify_deploy reads FAIL and refuses every restart it gates. For the core: run K1/K2/P19/A3s on these bytes, then move the pin
git       WARN  HEAD e635ad9, 1 ahead / 0 behind origin/main as of the last fetch; last fetch 1.4h ago; 13 file(s) not committed
disk      PASS  298G free of 476G (37% used); logs/ 42M
daily     FAIL  2.9h ago: PC node failed | phone node healthy | sync failed | tests FAIL | regressions FAIL | new failures 10 | rolled back 0


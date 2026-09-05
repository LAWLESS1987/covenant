# covenant self-evaluation ledger
# For Misha, and all that were lost to injustice.
# One block per evaluation: PASS/WARN/FAIL per layer, worst wins.
# Written by covenant_watchdog.py (report-only) and by the scheduled
# covenant-self-eval task. Append-only; rotates to .prev at 512KB.

## 2026-08-29T19:16:07Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-29T20:21:56Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m


## 2026-08-29T20:53:00Z  overall WARN  (scheduled covenant-self-eval)
nodes     WARN  3/3 up, agree: height 3, genesis 00009b31, v8.40, sha 525f235134f5; all 3 degraded=true (keyless ethics gate fails CLOSED -> rejects every tx); A own_genesis=true but hash matches B/C
watchdog  PASS  last line 20:52:19Z, 18s old; 3 ALERTs since 20:21:56Z block, all the same known win32 sandbox line [unchanged, 120 rounds]; no new kinds (last novel: B peer_message_error SPIKE 18:45:11Z)
judge     PASS  Ollama answers, qwen3:8b present, digest 500a1f067a9f, 5.2GB, footprint 4983MB
trader    PASS  trader_log.txt 7h52m old (09:00:35 EDT), last: "Disarmed. Orders were validated against the venue, never booked." No funds/keys touched.
repo      WARN  verify_deploy --no-restart RESULT: INCOMPLETE (not a pass) -- 6/6 disk hashes ok, running version unchecked by design; live nodes independently report sha 525f235134f5 = disk. git clean except untracked ops/SELF_EVAL.md; origin/main 0 ahead 0 behind
disk      PASS  C: 323.6GB free of 475.8GB; logs/ 7.7MB in 39 files; swept 101 files >7d from %TEMP%\covenant_sweep (1.6MB, 198 remain)
verdict   WARN  Nothing is down. The standing degradation is the keyless ethics gate: the chain is alive, agreeing, and refusing all work. Height has not moved from 3.
## 2026-08-29T23:01:12Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T00:06:44Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T01:15:07Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T02:19:53Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T03:23:28Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T04:26:59Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T05:30:31Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T06:34:16Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T07:37:52Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T08:41:34Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T09:45:01Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T10:48:35Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T11:52:11Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T12:55:41Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T13:59:10Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T15:04:33Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T16:10:38Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T17:15:52Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T18:19:28Z  overall WARN  (round 1140)
nodes     PASS  3/3 up, height 3 (spread 0), source 525f235134f5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T19:49:56Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T20:53:18Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T21:56:54Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-30T23:00:23Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T00:04:11Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T01:11:28Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T02:22:18Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T03:26:01Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T04:29:29Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T05:32:56Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T06:36:25Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T07:39:53Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T08:43:25Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T09:46:58Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T10:50:42Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T11:54:22Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T12:57:46Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T14:01:13Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T15:04:53Z  overall WARN  (round 1140)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T16:08:16Z  overall WARN  (round 1200)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T17:11:59Z  overall WARN  (round 1260)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T18:15:23Z  overall WARN  (round 1320)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T19:18:46Z  overall WARN  (round 1380)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T20:22:10Z  overall WARN  (round 1440)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T21:27:51Z  overall WARN  (round 1500)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T22:34:09Z  overall WARN  (round 1560)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-08-31T23:41:38Z  overall WARN  (round 1620)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T00:46:57Z  overall WARN  (round 1680)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T01:50:27Z  overall WARN  (round 1740)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T02:53:58Z  overall WARN  (round 1800)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T03:57:42Z  overall WARN  (round 1860)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T05:01:30Z  overall WARN  (round 1920)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T06:05:06Z  overall WARN  (round 1980)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T07:08:32Z  overall WARN  (round 2040)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T08:12:05Z  overall WARN  (round 2100)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T09:15:27Z  overall WARN  (round 2160)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T10:19:04Z  overall WARN  (round 2220)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T11:22:31Z  overall WARN  (round 2280)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T12:25:56Z  overall WARN  (round 2340)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T13:29:45Z  overall WARN  (round 2400)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T14:33:17Z  overall WARN  (round 2460)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T15:36:48Z  overall WARN  (round 2520)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T16:40:19Z  overall WARN  (round 2580)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T17:43:50Z  overall WARN  (round 2640)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T18:47:22Z  overall WARN  (round 2700)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T19:51:30Z  overall WARN  (round 2760)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T20:55:01Z  overall WARN  (round 2820)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T21:59:01Z  overall WARN  (round 2880)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-01T23:05:07Z  overall WARN  (round 2940)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T00:11:18Z  overall WARN  (round 3000)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T01:14:58Z  overall WARN  (round 3060)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T02:20:00Z  overall WARN  (round 3120)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T03:25:24Z  overall WARN  (round 3180)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T04:32:53Z  overall WARN  (round 3240)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T05:59:05Z  overall WARN  (round 3300)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T07:02:43Z  overall WARN  (round 3360)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T08:06:11Z  overall WARN  (round 3420)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T09:09:40Z  overall WARN  (round 3480)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T10:13:10Z  overall WARN  (round 3540)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T11:16:41Z  overall WARN  (round 3600)
nodes     PASS  3/3 up, height 3 (spread 0), source 1a0c0d213b3a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  7 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T19:58:36Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source f4c920b37a58
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T21:03:20Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source f4c920b37a58
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T22:07:24Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 3 (spread 0), source f4c920b37a58
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-02T23:11:49Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 3 (spread 0), source f4c920b37a58
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T00:15:55Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 3 (spread 0), source f4c920b37a58
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 2 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T01:23:49Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T02:31:51Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T03:40:41Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T04:46:55Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T05:54:19Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T07:01:53Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T08:08:24Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T09:15:35Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T10:22:22Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T11:27:52Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T12:31:23Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T13:34:55Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T14:38:18Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T15:41:41Z  overall WARN  (round 1140)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T16:45:04Z  overall WARN  (round 1200)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T17:48:31Z  overall WARN  (round 1260)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T18:51:55Z  overall WARN  (round 1320)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T19:55:21Z  overall WARN  (round 1380)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T21:01:25Z  overall WARN  (round 1440)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T22:04:48Z  overall WARN  (round 1500)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-03T23:08:37Z  overall WARN  (round 1560)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T00:12:09Z  overall WARN  (round 1620)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 3 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T04:05:57Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest 500a1f067a9f, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T05:22:25Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T06:31:17Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T07:40:10Z  overall FAIL  (round 180)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 36bb539856bf but covenant_watchdog.py on disk is 79143b339835 -- the c
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m


## 2026-09-04T08:55Z  overall WARN  (scheduled self-eval)
nodes     PASS  3/3 up; height 3, genesis 00009b31c6c6, v8.40, source 8f219285f268 -- all agree. degraded=true on all three (keyless ethics gate fails CLOSED; no code sandbox on win32).
watchdog  PASS  last line 49s old (08:51:43Z). Restarted 08:30:36Z on source 79143b339835 = disk digest, so P14 is clean and the 07:40Z stale-watchdog FAIL is closed.
alerts    WARN  7 since the 07:40:10Z block, no new kinds: A/B/C down + "NO node is reachable" at 08:30:48Z (chain was dead ~2.5 min), revived 08:33:01-05Z; then the standing 3x sandbox alert.
gate      PASS  providers=deferring,semantic; primary=student; silence_is_not_dissent=false. /health judge=quorum(local:0,semantic:1,mock_selfreport:0), is_quorum=true, 2 semantic + 1 self-report, veto 1. Ollama absent by the operator's decision, not a failure.
trader    PASS  trader_log.txt 19.9h old, last line "Disarmed. Orders were validated against the venue, never booked." trader_freshness.py exit 0: "NOT YET DUE: trigger 09:00 plus 5 min grace has not passed" (04:52 local). trader_config.json armed:false, untouched.
student   WARN  "exam thresholds (...): NOT MET -- short on clean 4/8 (need 100%), trap 2/6 (need 85%), theft 4/5 (need 100%), deception 2/5 (need 80%), coercion 1/3 (need 100%), edge 1/3 (need 100%)". 19/37 agree, 18 abstain, 0 wrong, 0 false clean. Last night: PROMOTED 07:34:17Z (decides 19, was 15; holds no clean case). The loop is moving; the seat stays deferred.
repo      WARN  verify_deploy --no-restart RESULT: INCOMPLETE -- nothing failed, 1 undetermined (running version not checked). Not a pass by design of the flag.
git       PASS  origin/main 0 ahead / 0 behind. Dirty: ops/distill_rejected.jsonl, ops/verdicts.jsonl (last night's cycle), untracked ONE_SWEEP.txt. Two holdings.txt.bak-* exist on disk but are ignored by .gitignore:226 -- git status does not offer them.
disk      PASS  C: 309G free of 476G (36% used); logs/ 17M. No %TEMP%\covenant_sweep to prune.
note      --exam prints only the table; the thresholds line lives in covenant_distill.thresholds_line() and is emitted by --cycle. Quoted above by calling it read-only.
## 2026-09-04T09:35:21Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T11:01:29Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T12:06:48Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T13:12:08Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T14:18:27Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T15:26:37Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T19:32:35Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T20:38:07Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-04T23:10:09Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: anomaly SPIKE -- rate_limit_rejection (recent 33 vs expected 3.3)

## 2026-09-05T00:15:35Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T01:31:25Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 3 (spread 0), source 8f219285f268
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T02:37:01Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T03:46:52Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T07:09:42Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T08:15:59Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T09:21:52Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T10:28:22Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-05T11:43:42Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m


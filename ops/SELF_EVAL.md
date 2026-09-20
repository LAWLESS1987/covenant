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

## 2026-09-05T13:47:07Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T03:19:30Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T04:25:25Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T05:31:19Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T06:37:38Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T07:41:24Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T08:44:52Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T09:48:26Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  6 live -- first: node A: restarted since the last check (uptime went backwards)

## 2026-09-06T10:51:55Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T11:55:20Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T12:58:53Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 3 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T14:26:15Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 6 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T15:29:43Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 7 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T17:18:51Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 7 (spread 0), source caf78bf86e88
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  4 live -- first: node A: code sandbox unavailable -- no usable 'fork' start method on this platform (win32), so the sandbox's m

## 2026-09-06T19:11:58Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-06T20:15:25Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-06T21:18:53Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-06T22:22:29Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-06T23:27:16Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T00:31:41Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T01:35:49Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T02:40:00Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T03:44:04Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T04:48:50Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T05:52:58Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T06:57:04Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T08:01:55Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T09:06:11Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T10:11:05Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T11:15:17Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T12:19:22Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 9 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T13:25:32Z  overall FAIL  (round 1080)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded cf77a3641c5c but covenant_watchdog.py on disk is f2c238f6579c -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded cf77a3641c5c but covenant_watchdog.py on disk is f2c238f6579

## 2026-09-07T14:31:09Z  overall FAIL  (round 1140)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded cf77a3641c5c but covenant_watchdog.py on disk is f2c238f6579c -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded cf77a3641c5c but covenant_watchdog.py on disk is f2c238f6579

## 2026-09-07T15:51:20Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T16:56:46Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T18:02:17Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T19:07:57Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T20:15:51Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T21:23:20Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T22:28:56Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-07T23:34:25Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T00:39:55Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T01:45:33Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T03:19:02Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T04:24:39Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T05:30:10Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T06:35:37Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T07:41:04Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T08:46:36Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs df84389b75b6, B runs df84389b75b6, C runs df84389

## 2026-09-08T09:52:03Z  overall FAIL  (round 1020)
nodes     PASS  3/3 up, height 10 (spread 0), source df84389b75b6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  2 live -- first: node(s) running a source that is NOT the one on disk: A runs df84389b75b6, B runs df84389b75b6, C runs df84389

## 2026-09-08T10:57:20Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T10:57:38Z  overall FAIL  (round 1080)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T12:02:59Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T12:03:18Z  overall FAIL  (round 1140)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T13:08:37Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T13:09:01Z  overall FAIL  (round 1200)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T14:14:15Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T14:14:45Z  overall FAIL  (round 1260)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T15:19:55Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T15:20:35Z  overall FAIL  (round 1320)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T16:25:33Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T16:26:18Z  overall FAIL  (round 1380)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T17:31:10Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T17:32:03Z  overall FAIL  (round 1440)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T18:36:48Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T18:37:44Z  overall FAIL  (round 1500)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T19:42:28Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T19:43:34Z  overall FAIL  (round 1560)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T20:48:25Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T20:49:31Z  overall FAIL  (round 1620)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-08T23:43:59Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-08T23:45:09Z  overall FAIL  (round 1680)
nodes     PASS  3/3 up, height 12 (spread 0), source e936de9d4c77
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded f2c238f6579c but covenant_watchdog.py on disk is 94e47e9c14c

## 2026-09-09T01:39:04Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T02:44:40Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T03:50:28Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T04:56:19Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T06:02:20Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T07:08:33Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T08:14:34Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T09:20:24Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T10:26:17Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T11:32:11Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T12:37:59Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 13 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T13:43:59Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-09T19:29:06Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T20:34:53Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T21:40:25Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T22:46:07Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-09T23:52:05Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T00:57:49Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T02:03:32Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T03:09:07Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T04:14:42Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T05:20:16Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T06:25:51Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T07:31:17Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-10T08:37:02Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T09:42:52Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T10:48:25Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 14 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T11:53:52Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 15 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T12:59:16Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 15 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T14:04:40Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T15:10:07Z  overall WARN  (round 1140)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T16:15:31Z  overall WARN  (round 1200)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T17:21:03Z  overall WARN  (round 1260)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T18:26:28Z  overall WARN  (round 1320)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T19:31:57Z  overall WARN  (round 1380)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T20:37:23Z  overall WARN  (round 1440)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T21:42:51Z  overall WARN  (round 1500)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T22:48:18Z  overall WARN  (round 1560)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-10T23:53:42Z  overall WARN  (round 1620)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 1e72206edd9a, B runs 1e72206edd9a, C runs 1e72206

## 2026-09-11T00:59:15Z  overall WARN  (round 1680)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T02:04:50Z  overall WARN  (round 1740)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T03:10:38Z  overall WARN  (round 1800)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T04:17:56Z  overall WARN  (round 1860)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T05:23:51Z  overall WARN  (round 1920)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T06:29:35Z  overall WARN  (round 1980)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T07:35:10Z  overall WARN  (round 2040)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T08:40:39Z  overall WARN  (round 2100)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T09:46:04Z  overall WARN  (round 2160)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a


## 2026-09-11T04:12Z  overall FAIL  (scheduled self-eval)
nodes     PASS  3/3 up (5000/5020/5060), height 16, genesis 00009b31, v8.40, all running source 1e72206edd9a; degraded=true on all three (no provider key, no code sandbox on win32)
watchdog  PASS  last line 2s old (2026-09-11T04:00:14Z, balance agreement A/B/C); 82 ALERTs since 09-10T00Z, 37 today. New kind since the last block: peer_message_error SPIKE on node A (09-10T23:14, 6 vs expected 0.8). Others recurring: rate_limit_rejection spikes, source-not-on-disk, mesh multi-source.
gate      PASS  ops/quorum_policy.json: providers deferring,semantic; primary=student; silence_is_not_dissent=false; github_when_local_down=false; ollama_in_chain=false. All three /health report judge quorum(local:0,semantic:1,mock_selfreport:0), is_quorum=true, 2 semantic + 1 self-report. Ollama absent by the operator's decision -- disclosed, not failed.
trader    PASS  trader_log.txt 15.0h old, last line "---- CYCLE COMPLETE 09/10/2026 ----". trader_freshness.py exit 0: "NOT YET DUE: trigger 09:00 plus 5 min grace has not passed" (ran at 00:00 local). Rule 5 still blocks: 3 settled signals of 30 needed, 0/3 wins, mean -5.92% after costs, p=1.000. NOTE: trader_config.json reads armed=true (armed 2026-09-06 by FUTURE.bat), not armed=false as this task's file states; nothing can trade while Rule 5 is short.
student   PASS  loop working. --exam decides 36/53 (0 false clean, 7 false hold, all in `discourse`). Thresholds NOT MET -- short on clean 7/8, trap 5/6, theft 4/5, edge 1/3. ops/DISTILL.md 2026-09-11T07:51:37Z: PROMOTED (no false clean, cleared 139/353 unseen rows with 0 wrong). Seat stays with the deferring chain.
repo      FAIL  verify_deploy.py --no-restart RESULT: FAIL -- 4 hash mismatches (covenant_unified_v8.py, run_all_tests.sh, test_a3s_send_bounds.py, test_p15_judge_identity.py). Cause is stale pins, not tamper: the pins in verify_deploy.py were last edited 2026-09-04 and 7 commits have touched covenant_unified_v8.py since. Disk hashes 57d877e3f7a6 and is clean against HEAD.
mesh      NOTE  the "foreign" peer source 57d877e3f7a6 at 10.0.0.174 is the CURRENT disk source. The three local nodes are the stale ones: they still run 1e72206edd9a and were never restarted onto the committed code.
git       WARN  branch a9-support-ticket-filed, 2 ahead / 0 behind origin/main. 10 modified (all loop-written ledgers/models), 3 untracked: ops/outbound_overrides.jsonl, ops/strategy_reports/NIGHTLY_2026-09-{10,11}.txt, w2_w2off.err. No holdings/portfolio file among them.
disk      PASS  C: 314G free of 476G (35% used); logs/ 23M; no %TEMP%\covenant_sweep to prune.
## 2026-09-11T10:51:36Z  overall WARN  (round 2220)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T11:57:03Z  overall WARN  (round 2280)
nodes     PASS  3/3 up, height 16 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T13:02:28Z  overall WARN  (round 2340)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T14:07:57Z  overall WARN  (round 2400)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T15:13:29Z  overall WARN  (round 2460)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T16:18:58Z  overall WARN  (round 2520)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T17:24:27Z  overall WARN  (round 2580)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T18:29:57Z  overall WARN  (round 2640)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T19:35:29Z  overall WARN  (round 2700)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T20:40:59Z  overall WARN  (round 2760)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a



## 2026-09-11T21:38Z  overall FAIL  (scheduled self-eval)
nodes     PASS  3/3 up (5000/5020/5060), height 17 all three (spread 0), genesis 00009b31, v8.40, all running source 1e72206edd9a, is_quorum=true. degraded=true on all three (no provider key, no win32 code sandbox) -- unchanged.
watchdog  PASS  last line 54s old (21:35:38Z, balance agreement A/B/C: 988/12/0). 64 ALERTs since the 04:12Z block; only two kinds, both recurring (source-not-on-disk, mesh multi-source). No new kind -- 09-10's peer_message_error SPIKE has not recurred.
gate      PASS  ops/quorum_policy.json: providers deferring,semantic; primary=student; silence_is_not_dissent=false; github_when_local_down=false; ollama_in_chain=false; relax_valueless_for_local_nodes=true. All three /health: quorum(local:0,semantic:1,mock_selfreport:0), 2 semantic + 1 self-report, degradations []. Ollama absent by the operator's decision -- disclosed, not failed.
trader    PASS  trader_log.txt 8h37m old; the 09:00 cycle COMPLETED (trader-printed, not launcher). trader_freshness.py exit 0: "RAN: a cycle dated 2026-09-11 COMPLETED". No orders: cash_floor BLOCK, R4/R6 held, XRP sell dropped at the frozen floor; sealed ok (tx 2e7dc64f2188). Rule 5 unchanged: 3/30 settled, 0/3 wins, mean -5.92% after costs, p=1.000. NOTE (3rd block running): trader_config.json reads armed=true (2026-09-06 by FUTURE.bat), not armed=false as this task file states -- the task file is stale, not the config. No funds or keys touched.
student   PASS  loop working. --exam: 36/53 agree, 0 false clean, 7 false hold (all in `discourse`), 10 abstain. Thresholds NOT MET -- short on clean 7/8, trap 5/6, theft 4/5, edge 1/3. ops/DISTILL.md {2026-09-11T13:46:47Z}: PROMOTED (no false clean, holds no clean case, 2178 held-out rows with 55 false clears, no prior record to beat). Seat stays with the deferring chain.
repo      FAIL  verify_deploy.py --no-restart RESULT: FAIL -- same 4 hash mismatches as 04:12Z (covenant_unified_v8.py 57d877e3f7a6 vs pinned 8f219285f268, run_all_tests.sh, test_a3s_send_bounds.py, test_p15_judge_identity.py). Cause is stale pins in verify_deploy.py, not tamper: those files were last committed 09-10 (A81) and 09-09 and the working tree is clean against HEAD. Companions all present.
mesh      NOTE  three source generations in play: local nodes run 1e72206edd9a, disk is 57d877e3f7a6, the tested pins expect 8f219285f268. The "foreign" peer at 10.0.0.174 runs the disk source -- the local three are the stale ones, never restarted onto the committed code.
git       WARN  branch fix/judge-evidence-cut, 4 ahead / 0 behind origin/main. 2 modified (ops/NIGHTLY.md, ops/SELF_EVAL.md -- loop-written), 3 untracked: ops/outbound_overrides.jsonl, ops/strategy_reports/NIGHTLY_2026-09-{10,11}.txt, w2_w2off.err. No portfolio file untracked (holdings.txt.bak-* covered by .gitignore:227 *.bak-2*).
disk      PASS  C: 318G free of 476G (34% used); logs/ 23M; no %TEMP%\covenant_sweep to prune.
method    NOTE  the first shell read of this run returned an internally CONSISTENT view 11h stale (clock 10:30Z, watchdog tail 10:29Z, height 16). Caught only by cross-checking a second process (21:36Z, height 17, trader_freshness 17:35 local). A freshness check that compares a log tail to a clock from the same read can agree with itself and still be 11 hours wrong.
## 2026-09-11T21:46:35Z  overall WARN  (round 2820)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-11T22:53:39Z  overall WARN  (round 2880)
nodes     PASS  3/3 up, height 17 (spread 0), source 1e72206edd9a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 1e72206edd9a, peers report ['57d877e3f7a6'] -- peers on a

## 2026-09-12T00:42:44Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T01:48:18Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T02:53:44Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T03:59:09Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T05:04:38Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T06:10:03Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T07:15:41Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T08:21:30Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 57d877e3f7a6, peers report ['3e790328355b'] -- peers on a

## 2026-09-12T09:27:08Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 57d877e3f7a6, peers report ['3e790328355b'] -- peers on a

## 2026-09-12T10:32:34Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 17 (spread 0), source 57d877e3f7a6
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 57d877e3f7a6, peers report ['3e790328355b'] -- peers on a


## 2026-09-12T10:35:02Z  overall FAIL  (claude scheduled self-eval)
nodes     PASS  3/3 answer; height 17 spread 0; genesis 00009b31c6c6; v8.40; all run source 57d877e3f7a6; all degraded=true (no provider key, no win32 code sandbox)
mesh      WARN  node A still tracks a peer on source 3e790328355b at 127.0.0.1:? (A7) and reports own_genesis; B and C see only 57d877e3f7a6
watchdog  PASS  last line 17s old (10:34:xxZ); 8 ALERTs since the 08:21:30Z block, 2 kinds, both the source-drift pair repeating [unchanged, 120 rounds]; no new kinds
judge     PASS  wired as ops/quorum_policy.json says: providers deferring,semantic; primary student; github_when_local_down=false; silence_is_not_dissent=false; nodes report quorum=true (2 semantic + 1 self_report). Ollama absent by instruction -- disclosed, not failed
trader    PASS  trader_log.txt 2026-09-11T09:00:03 local, last line "---- CYCLE COMPLETE 09/11/2026 ----"; trader_freshness exit 0: "NOT YET DUE: trigger 09:00 plus 5 min grace has not passed" (checked 06:35 local). NOTE: trader_config.json reads armed:true (FUTURE.bat, 2026-09-06), not armed:false as this task's text assumes; min_sealed_signals 30 is what blocks. Not touched
student   WARN  covenant_distill.py --exam prints only the table, no thresholds line; ops/DISTILL.md's is NOT MET -- short on clean 7/8, trap 5/6, theft 4/5, edge 1/3. 36/53 agree, 0 false clean, 7 false hold (all discourse). Last cycle 2026-09-12T07:52:28Z PROMOTED (loop working)
repo      FAIL  verify_deploy --no-restart RESULT: FAIL -- covenant_unified_v8.py hash mismatch: on disk 3e790328355b, expected 57d877e3f7a6. Uncommitted 14-line A96 addition (print "SYNC REFUSED block N" to stderr). MANIFEST.sha256 already regenerated to 3e7903, verify_deploy.py:73 still pins 57d877 -- the two integrity records disagree
git       WARN  0 ahead / 0 behind origin/main; 10 modified, 5 untracked (ops/outbound_overrides.jsonl, 3 NIGHTLY reports, w2_w2off.err). No holdings/portfolio file among them
disk      PASS  C: 320.8 GB free of 475.8; logs/ 23.2 MB in 51 files; %TEMP%\covenant_sweep does not exist (nothing to prune)
verdict   FAIL  nodes are healthy and running the TESTED build; the disk copy is an unverified hand edit. Next: decide the A96 print, then re-pin and re-test -- do not restart nodes onto 3e7903 first
## 2026-09-12T11:38:07Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 17 (spread 0), source 73e4a0ce0b7a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-12T13:36:49Z  overall FAIL  (round 60)
nodes     PASS  3/3 up, height 18 (spread 0), source 73e4a0ce0b7a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 291bc76e675f -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 291bc76e675

## 2026-09-12T14:42:23Z  overall FAIL  (round 120)
nodes     PASS  3/3 up, height 18 (spread 0), source 73e4a0ce0b7a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is c677692ac4d8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is c677692ac4d

## 2026-09-12T15:47:54Z  overall FAIL  (round 180)
nodes     PASS  3/3 up, height 18 (spread 0), source 73e4a0ce0b7a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is c677692ac4d8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is c677692ac4d

## 2026-09-12T16:53:30Z  overall FAIL  (round 240)
nodes     PASS  3/3 up, height 18 (spread 0), source 73e4a0ce0b7a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 8ae964dae741 -- the c
alerts    WARN  2 live -- first: node(s) running a source that is NOT the one on disk: A runs 73e4a0ce0b7a, B runs 73e4a0ce0b7a, C runs 73e4a0c

## 2026-09-12T17:59:10Z  overall FAIL  (round 300)
nodes     PASS  3/3 up, height 18 (spread 0), source 182ffa5e1e1a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd3 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd

## 2026-09-12T19:04:46Z  overall FAIL  (round 360)
nodes     PASS  3/3 up, height 18 (spread 0), source 182ffa5e1e1a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd3 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd

## 2026-09-12T20:10:17Z  overall FAIL  (round 420)
nodes     PASS  3/3 up, height 18 (spread 0), source 182ffa5e1e1a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd3 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd

## 2026-09-12T21:26:28Z  overall FAIL  (round 480)
nodes     PASS  3/3 up, height 18 (spread 0), source 182ffa5e1e1a
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd3 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd

## 2026-09-13T00:05:16Z  overall FAIL  (round 540)
nodes     PASS  3/3 up, height 18 (spread 0), source 1b697694310c
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     WARN  no local judge baseline; the seat defers per ops/quorum_policy.json (GitHub runner, then the distilled fallback; silence is not dissent)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd3 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 1daa524879db but covenant_watchdog.py on disk is 3a98f0ab5dd

## 2026-09-13T01:14:18Z  overall PASS  (round 60)
nodes     PASS  3/3 up, height 18 (spread 0), source 138311e283c3
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-13T02:17:46Z  overall PASS  (round 120)
nodes     PASS  3/3 up, height 18 (spread 0), source 138311e283c3
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-13T03:21:14Z  overall FAIL  (round 180)
nodes     PASS  3/3 up, height 19 (spread 0), source 8a5d7974159b
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T04:24:42Z  overall FAIL  (round 240)
nodes     PASS  3/3 up, height 19 (spread 0), source 8a5d7974159b
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T05:28:07Z  overall FAIL  (round 300)
nodes     PASS  3/3 up, height 19 (spread 0), source 8a5d7974159b
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T06:31:30Z  overall FAIL  (round 360)
nodes     PASS  3/3 up, height 19 (spread 0), source 8a5d7974159b
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T07:34:51Z  overall FAIL  (round 420)
nodes     PASS  3/3 up, height 19 (spread 0), source 8a5d7974159b
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@06402c3a74c, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T08:38:19Z  overall FAIL  (round 480)
nodes     PASS  3/3 up, height 20 (spread 0), source 8a5d7974159b
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed


## 2026-09-13T08:56Z  overall FAIL  (claude scheduled self-eval)
nodes     PASS  3/3 up (5000/5020/5060), height 20 all three (spread 0), genesis 00009b31, v8.40, all running source 27a9bf2b01ad -- which IS the file on disk. degraded=true on all three (no provider key, no win32 code sandbox); A also flags own_genesis + anomaly kinds peer_message_error/peer_version_mismatch, B the same two, C none. Free RAM 5993-6231 MB
watchdog  PASS  last line 2026-09-13T08:52:06Z, 47s before the check (balance agreement A/B/C 988/12/0). 93 ALERTs since the 09-12T10:35Z block, 46 of them today. Recurring: watchdog-stale (14), node restarts (15 across A/B/C), mesh multi-source (11), source-not-on-disk (4). THREE NEW KINDS since the last block: "NO node is reachable -- the chain is not running" plus per-node :5000/:5020/:5060 unreachable (a real gap, then the nodes came back on the current source); "node A/B: substrate reading is ~5440s old"; "node A anomaly SPIKE -- bridge_message_error 6 vs expected 1.8" (17071, CLEARED after 1 round at 04:35:16Z)
gate      PASS  ops/quorum_policy.json: providers deferring,semantic; primary=student; silence_is_not_dissent=false; github_when_local_down=false; ollama_in_chain=false; relax_valueless_for_local_nodes=true. All three /health agree: quorum(local:0,semantic:1,mock_selfreport:0), is_quorum=true, 2 semantic + 1 self-report, veto_threshold 1, degradations []. Ollama absent by the operator's 2026-09-07 instruction -- disclosed, not failed
trader    PASS  trader_log.txt 2026-09-12T09:00:03 local (19h53m old), last line "---- CYCLE COMPLETE 09/12/2026 ----". trader_freshness exit 0: "NOT YET DUE: trigger 09:00 plus 5 min grace has not passed" (checked 04:53 local). NOTE (4th block running): trader_config.json reads armed:true (FUTURE.bat, 2026-09-06), NOT armed:false as this task file states -- the task text is stale, the config is the operator's. Rule 5 / min_sealed_signals is what blocks. No funds, keys or orders touched
student   WARN  loop working. --exam prints the table only, no thresholds line (same as 09-12): 53 cases, 38 agree, 0 false clean, 7 false hold (all `discourse`), 8 abstain. Thresholds from ops/DISTILL.md: NOT MET -- short on clean 7/8 (need 100%), trap 5/6 (need 85%), edge 2/3 (need 100%). theft/deception/coercion/injection now 19/19. Last cycle 2026-09-13T07:52:11Z PROMOTED (exam 38, was 36; model 1cdc0ebb73bc, 3470 examples). Seat stays with the deferring chain
repo      FAIL  verify_deploy.py --no-restart RESULT: FAIL -- 4 problems: covenant_unified_v8.py, run_all_tests.sh and run_local_sweep.py hash mismatch, test_p15_judge_identity.py missing. Cause is STALE PINS, not tamper: verify_deploy.py:73-142 still pins a 2026-09-04 build and still requires test_p15_judge_identity.py, which was deliberately deleted in eb892c0 (Ollama removal batch 4/5) and is absent from HEAD. MANIFEST.sha256 records 27a9bf2b01ad for covenant_unified_v8.py, which is what disk holds and what all three nodes run -- the two integrity records disagree, and the manifest is the one telling the truth
git       WARN  on main, 0 ahead / 0 behind origin/main after fetch -- but 7 files sit STAGED AND UNCOMMITTED (MANIFEST.sha256, covenant_unified_v8.py +34 lines vs HEAD, covenant_nightly.py, .gitignore, docs/DAILY_PLAN.md, docs/KNOWN_ISSUES.md, pending-v8.38/, new covenant_app_update.py). A prior session staged a batch and never committed it; the running chain is on that unreviewed code. 9 loop-written modified, 6 untracked (ops/RUN_WITHOUT.json, outbound_overrides.jsonl, 4 nightly strategy reports). No holdings/portfolio file untracked
disk      PASS  C: 323G free of 476G (33% used); logs/ 25M; no %TEMP%\covenant_sweep directory to prune
verdict   FAIL  on repo only. Nothing is down: three nodes, a fresh watchdog, a wired gate and a trader that is not due. The failure is bookkeeping -- verify_deploy.py has been pinning a dead build and a deleted test for nine days, so it now cries wolf every run and cannot see a real substitution
## 2026-09-13T09:41:53Z  overall FAIL  (round 540)
nodes     PASS  3/3 up, height 20 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T10:45:22Z  overall FAIL  (round 600)
nodes     PASS  3/3 up, height 20 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T11:48:55Z  overall FAIL  (round 660)
nodes     PASS  3/3 up, height 20 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T12:53:36Z  overall FAIL  (round 720)
nodes     PASS  3/3 up, height 20 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T13:57:33Z  overall FAIL  (round 780)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T15:01:11Z  overall FAIL  (round 840)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T16:04:39Z  overall FAIL  (round 900)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T17:08:07Z  overall FAIL  (round 960)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T18:11:37Z  overall FAIL  (round 1020)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T19:15:05Z  overall FAIL  (round 1080)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T20:18:35Z  overall FAIL  (round 1140)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T21:22:05Z  overall FAIL  (round 1200)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T22:25:33Z  overall FAIL  (round 1260)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-13T23:29:02Z  overall FAIL  (round 1320)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-14T00:32:33Z  overall FAIL  (round 1380)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-14T01:36:04Z  overall FAIL  (round 1440)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-14T02:39:35Z  overall FAIL  (round 1500)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed8 -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded 3a98f0ab5dd3 but covenant_watchdog.py on disk is 9a0668bc9ed

## 2026-09-14T04:07:56Z  overall FAIL  (round 60)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 9a0668bc9ed8 but covenant_watchdog.py on disk is 79e12eb5c4cd -- the c
alerts    WARN  2 live -- first: node(s) running a source that is NOT the one on disk: A runs 27a9bf2b01ad, B runs 27a9bf2b01ad, C runs 27a9bf2

## 2026-09-14T05:11:29Z  overall FAIL  (round 120)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 9a0668bc9ed8 but covenant_watchdog.py on disk is 79e12eb5c4cd -- the c
alerts    WARN  3 live -- first: phone phone: SILENT for 117 min after reporting (last: height 12) -- the node or the app stopped, or the Wi-Fi

## 2026-09-14T06:15:02Z  overall FAIL  (round 180)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 9a0668bc9ed8 but covenant_watchdog.py on disk is 79e12eb5c4cd -- the c
alerts    WARN  3 live -- first: phone phone: SILENT for 181 min after reporting (last: height 12) -- the node or the app stopped, or the Wi-Fi

## 2026-09-14T07:18:33Z  overall FAIL  (round 240)
nodes     PASS  3/3 up, height 22 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 9a0668bc9ed8 but covenant_watchdog.py on disk is 79e12eb5c4cd -- the c
alerts    WARN  3 live -- first: phone phone: SILENT for 244 min after reporting (last: height 12) -- the node or the app stopped, or the Wi-Fi

## 2026-09-14T08:22:09Z  overall FAIL  (round 300)
nodes     PASS  3/3 up, height 23 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 9a0668bc9ed8 but covenant_watchdog.py on disk is 79e12eb5c4cd -- the c
alerts    WARN  3 live -- first: phone phone: SILENT for 308 min after reporting (last: height 12) -- the node or the app stopped, or the Wi-Fi

## 2026-09-14T10:01:35Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 23 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 27a9bf2b01ad, B runs 27a9bf2b01ad, C runs 27a9bf2

## 2026-09-14T11:04:56Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 23 (spread 0), source 27a9bf2b01ad
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node(s) running a source that is NOT the one on disk: A runs 27a9bf2b01ad, B runs 27a9bf2b01ad, C runs 27a9bf2

## 2026-09-14T12:08:21Z  overall FAIL  (round 180)
nodes     PASS  3/3 up, height 23 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 79e12eb5c4cd but covenant_watchdog.py on disk is 9a97ab9d0b3b -- the c
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T13:11:50Z  overall FAIL  (round 240)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=1, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded 79e12eb5c4cd but covenant_watchdog.py on disk is c84c64e56b3e -- the c
alerts    WARN  8 live -- first: node A: anomaly SPIKE -- rate_limit_rejection (recent 42 vs expected 8.9)

## 2026-09-14T14:35:29Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T16:09:40Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T17:12:57Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T18:16:16Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: 1 peer(s) unreachable -- heartbeats backed off

## 2026-09-14T19:19:34Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T20:22:58Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T21:26:21Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T22:29:47Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1cdc0ebb73b, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-14T23:33:17Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T00:37:47Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T01:41:26Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a


## 2026-09-15T02:08Z  overall FAIL  (claude scheduled self-eval)
nodes     PASS  3/3 up (5000/5020/5060), height 24 all three (spread 0), genesis 00009b31, v8.40, all on source 2f5e4e914bb5, 11510 lines. degraded=true on all three (no provider key, no win32 code sandbox) -- disclosed, unchanged. anomaly_kinds empty everywhere; A skipped 3 heartbeats; free RAM 4943-5412 MB
watchdog  PASS  last line 2026-09-15T02:07:51Z, 6s before the check (balance agreement A/B/C 988/12/0). 434 ALERTs since the 09-13T08:56Z block. ONE NEW KIND, and it is the big one: "phone phone: SILENT ... (last: height 12)" ran ~250 consecutive lines, 60 min -> 344 min, plus "UNEXPECTED PEER peer_100.86.158.1_5001 ... POST /peers requires an operator signature" at 13:18Z. The phone is back (last seen 8 min ago, battery 100) but still at height 12 -- 12 blocks behind. Other recurring: watchdog-stale (62, now clear), mesh multi-source (31), source-not-on-disk (23), node down A/B/C (1 each), rate_limit_rejection + peer_message_error spikes
gate      PASS  ops/quorum_policy.json: providers deferring,semantic; primary=student; silence_is_not_dissent=false; github_when_local_down=false; ollama_in_chain=false; relax_valueless_for_local_nodes=true. All three /health agree: quorum(local:0,semantic:1,mock_selfreport:0), is_quorum=true, 2 semantic + 1 self-report, veto_threshold 1, degradations []. Ollama absent by the operator's 2026-09-07 instruction -- disclosed, not failed
trader    PASS  trader_log.txt 2026-09-14T09:00:03 local (13h08m old), last line "---- CYCLE COMPLETE 09/14/2026 ----". trader_freshness.py exit 0: "RAN: a cycle dated 2026-09-14 COMPLETED -- the trader printed it, not the launcher." After 09:05, so this is the strong form. NOTE (5th block running): trader_config.json reads armed=true (FUTURE.bat, 2026-09-06T13:42Z), NOT armed:false as this task file states -- the task text is stale, the config is the operator's. min_sealed_signals=30 / Rule 5 is what blocks. No funds, keys or orders touched
student   WARN  exam thresholds (judge_suite.THRESHOLDS, abstain counts as a miss; 1 wordless case excluded): NOT MET -- short on clean 7/8 (need 100%), trap 5/6 (need 85%), edge 2/3 (need 100%). 53 cases, 38 agree, 7 wrong (all `discourse`), 0 false clean, 8 abstain; theft/deception/coercion/injection 19/19. Last nightly cycle 2026-09-14T07:46:07Z REFUSED -- the loop working. Then a deliberate BASELINE RESET at 22:39Z (1cdc0ebb73bc -> 83851a41686e, same 38/53, better held-out behaviour under the new stopword/doc-frequency rules). Seat stays with the deferring chain. CLI gap, 3rd block running: `--exam` prints the table only, never the thresholds line this task asks me to quote (covenant_distill.py:1355-1358 calls table() but not thresholds_line())
repo      FAIL  verify_deploy.py --no-restart RESULT: FAIL -- 4 problems: covenant_unified_v8.py, run_all_tests.sh, run_local_sweep.py hash mismatch; test_p15_judge_identity.py missing. STALE PINS, not tamper, and now provably chronic: the MANIFEST block (verify_deploy.py:53-80) was last re-pinned 2026-09-11 for a 11214-line core, disk is 11510; and it still REQUIRES test_p15_judge_identity.py, deleted on purpose in eb892c0 (2026-09-12) -- the same commit that last edited verify_deploy.py. A verifier that fails every run cannot see a real substitution
git       PASS  on main, 0 ahead / 0 behind origin/main after fetch. The 7 staged-uncommitted files flagged on 09-13 are COMMITTED and pushed (HEAD 9cf3f15). 7 loop-written modified (fallback_model_2.json, ops/DISTILL_2.md, HOLDOUT_2.json, NIGHTLY.md, SELF_EVAL.md, distill_rejected.jsonl, verdicts.jsonl), 7 untracked (ops/RUN_WITHOUT.json, outbound_overrides.jsonl, 5 nightly strategy reports). No holdings/portfolio file untracked -- the two holdings.txt.bak-* on disk are covered by .gitignore:227 (*.bak-2*)
disk      PASS  C: 307G free of 476G (36% used); logs/ 27M; no %TEMP%\covenant_sweep directory to prune
verdict   FAIL  on repo only, for the second evaluation running, and for the same reason I named on 09-13 -- nothing was done about it. Nothing is down: three nodes agreeing at height 24, a 6-second-old watchdog, a wired gate, a trader that ran and refused. The two real items are (1) the deploy verifier pinning a dead build, and (2) the phone node 12 blocks behind on the old source, which is what has been generating the mesh multi-source alert for three days
## 2026-09-15T02:44:52Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T03:48:16Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T04:51:42Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T05:55:09Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T06:58:26Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 24 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@83851a41686, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T08:01:48Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 25 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T09:05:04Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 25 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T10:08:20Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 25 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T11:58:44Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 25 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T13:02:08Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T14:05:31Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T15:08:55Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T16:12:18Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T17:15:49Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T18:19:13Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T19:22:47Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T20:26:15Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T21:29:39Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T22:33:03Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-15T23:36:27Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T00:40:00Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T01:43:36Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T02:47:05Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T03:50:31Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T04:53:55Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T05:57:22Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T07:00:56Z  overall WARN  (round 1140)
nodes     PASS  3/3 up, height 26 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@3100c521fb2, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T08:04:32Z  overall WARN  (round 1200)
nodes     PASS  3/3 up, height 27 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T09:07:57Z  overall WARN  (round 1260)
nodes     PASS  3/3 up, height 27 (spread 0), source 2f5e4e914bb5
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 2f5e4e914bb5, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T10:11:25Z  overall FAIL  (round 1320)
nodes     PASS  3/3 up, height 27 (spread 0), source 3fb031657a8c
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded f6091f387f79 but covenant_watchdog.py on disk is 79925e8d8e0f -- the c
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 3fb031657a8c, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T13:49:14Z  overall WARN  (round 60)
nodes     PASS  3/3 up, height 28 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are ddfaaa9f704f, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T14:55:19Z  overall WARN  (round 120)
nodes     PASS  3/3 up, height 28 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  5 live -- first: node A: mesh is running more than one source: we are ddfaaa9f704f, peers report ['27a9bf2b01ad'] -- peers on a

## 2026-09-16T18:53:52Z  overall PASS  (round 60)
nodes     PASS  3/3 up, height 29 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-16T19:59:54Z  overall PASS  (round 120)
nodes     PASS  3/3 up, height 29 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-16T21:06:03Z  overall PASS  (round 180)
nodes     PASS  3/3 up, height 29 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-16T22:36:49Z  overall PASS  (round 60)
nodes     PASS  3/3 up, height 29 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-16T23:42:59Z  overall PASS  (round 120)
nodes     PASS  3/3 up, height 29 (spread 0), source ddfaaa9f704f
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass

## 2026-09-17T00:48:34Z  overall WARN  (round 180)
nodes     PASS  3/3 up, height 29 (spread 0), source 31b6e8131bd0
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@c4854e5da08, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 31b6e8131bd0, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T01:54:17Z  overall WARN  (round 240)
nodes     PASS  3/3 up, height 30 (spread 0), source 4737e38aa7da
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@e0578647fec, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 4737e38aa7da, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T02:59:32Z  overall WARN  (round 300)
nodes     PASS  3/3 up, height 30 (spread 0), source 4737e38aa7da
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@e0578647fec, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 4737e38aa7da, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T04:06:18Z  overall WARN  (round 360)
nodes     PASS  3/3 up, height 30 (spread 0), source 4737e38aa7da
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@e0578647fec, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 4737e38aa7da, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T05:13:01Z  overall WARN  (round 420)
nodes     PASS  3/3 up, height 30 (spread 0), source 4737e38aa7da
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@e0578647fec, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 4737e38aa7da, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T06:19:41Z  overall WARN  (round 480)
nodes     PASS  3/3 up, height 30 (spread 0), source 4737e38aa7da
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@e0578647fec, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 4737e38aa7da, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T07:30:22Z  overall WARN  (round 540)
nodes     PASS  3/3 up, height 30 (spread 0), source 4737e38aa7da
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@e0578647fec, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 4737e38aa7da, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T08:35:56Z  overall WARN  (round 600)
nodes     PASS  3/3 up, height 31 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@cc241f093a6, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T09:42:09Z  overall WARN  (round 660)
nodes     PASS  3/3 up, height 31 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@cc241f093a6, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T10:50:35Z  overall WARN  (round 720)
nodes     PASS  3/3 up, height 31 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@cc241f093a6, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T11:59:25Z  overall WARN  (round 780)
nodes     PASS  3/3 up, height 31 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@cc241f093a6, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T13:05:40Z  overall WARN  (round 840)
nodes     PASS  3/3 up, height 32 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@cc241f093a6, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T14:12:08Z  overall WARN  (round 900)
nodes     PASS  3/3 up, height 33 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@cc241f093a6, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T15:19:56Z  overall WARN  (round 960)
nodes     PASS  3/3 up, height 33 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T16:33:05Z  overall WARN  (round 1020)
nodes     PASS  3/3 up, height 33 (spread 0), source 51a6f4eb844d
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 51a6f4eb844d, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T17:55:31Z  overall WARN  (round 1080)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T19:11:08Z  overall WARN  (round 1140)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T20:17:28Z  overall WARN  (round 1200)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T21:27:26Z  overall WARN  (round 1260)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T22:38:24Z  overall WARN  (round 1320)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-17T23:48:05Z  overall WARN  (round 1380)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T00:54:28Z  overall WARN  (round 1440)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T02:00:53Z  overall WARN  (round 1500)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T03:07:25Z  overall WARN  (round 1560)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T04:13:46Z  overall WARN  (round 1620)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T05:20:04Z  overall WARN  (round 1680)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T06:26:32Z  overall WARN  (round 1740)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T07:32:52Z  overall WARN  (round 1800)
nodes     PASS  3/3 up, height 33 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@b5c91027271, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T08:39:24Z  overall WARN  (round 1860)
nodes     PASS  3/3 up, height 34 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T09:46:01Z  overall WARN  (round 1920)
nodes     PASS  3/3 up, height 34 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T10:52:29Z  overall WARN  (round 1980)
nodes     PASS  3/3 up, height 34 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T11:58:57Z  overall WARN  (round 2040)
nodes     PASS  3/3 up, height 34 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T13:05:17Z  overall WARN  (round 2100)
nodes     PASS  3/3 up, height 35 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T14:11:43Z  overall WARN  (round 2160)
nodes     PASS  3/3 up, height 35 (spread 0), source 7b12fe509061
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 7b12fe509061, peers report ['ddfaaa9f704f'] -- peers on a

## 2026-09-18T15:18:40Z  overall WARN  (round 2220)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 3

## 2026-09-18T15:18:40Z  overall WARN  (round 2220)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 3

## 2026-09-18T16:29:21Z  overall WARN  (round 2280)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 7

## 2026-09-18T16:29:21Z  overall WARN  (round 2280)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 7

## 2026-09-18T17:35:41Z  overall WARN  (round 2340)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 9

## 2026-09-18T17:35:41Z  overall WARN  (round 2340)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 9

## 2026-09-18T18:42:01Z  overall WARN  (round 2400)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 1

## 2026-09-18T18:42:01Z  overall WARN  (round 2400)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 1

## 2026-09-18T19:48:19Z  overall WARN  (round 2460)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 1

## 2026-09-18T19:48:19Z  overall WARN  (round 2460)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 1

## 2026-09-18T20:57:28Z  overall WARN  (round 2520)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 8

## 2026-09-18T22:04:02Z  overall WARN  (round 2580)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 1

## 2026-09-18T23:10:29Z  overall WARN  (round 2640)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 2

## 2026-09-19T00:16:52Z  overall WARN  (round 2700)
nodes     PASS  3/3 up, height 35 (spread 0), source 8cfd98921b40
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 8cfd98921b40, peers report ['ddfaaa9f704f'] (last heard 4

## 2026-09-19T01:30:56Z  overall WARN  (round 2760)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['ddfaaa9f704f'] (last heard 4

## 2026-09-19T01:30:56Z  overall WARN  (round 2760)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['ddfaaa9f704f'] (last heard 4

## 2026-09-19T02:40:40Z  overall WARN  (round 2820)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['ddfaaa9f704f'] (last heard 3

## 2026-09-19T03:47:43Z  overall WARN  (round 2880)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['ddfaaa9f704f'] (last heard 9

## 2026-09-19T04:55:10Z  overall WARN  (round 2940)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['8cfd98921b40'] (last heard 5

## 2026-09-19T06:02:34Z  overall WARN  (round 3000)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['8cfd98921b40'] (last heard 2

## 2026-09-19T07:09:56Z  overall WARN  (round 3060)
nodes     PASS  3/3 up, height 35 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@1d6d0cb1c52, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['8cfd98921b40'] (last heard 1

## 2026-09-19T08:16:59Z  overall WARN  (round 3120)
nodes     PASS  3/3 up, height 36 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['8cfd98921b40'] (last heard 4

## 2026-09-19T09:34:33Z  overall WARN  (round 3180)
nodes     PASS  3/3 up, height 36 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['8cfd98921b40'] (last heard 2

## 2026-09-19T10:47:08Z  overall WARN  (round 3240)
nodes     PASS  3/3 up, height 36 (spread 0), source 44f17e1c3e9b
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 44f17e1c3e9b, peers report ['8cfd98921b40'] (last heard 5

## 2026-09-19T11:59:44Z  overall WARN  (round 3300)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 0f388bd9eeaa, peers report ['8cfd98921b40'] (last heard 4

## 2026-09-19T13:09:49Z  overall WARN  (round 3360)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  2 live -- first: node A: mesh is running more than one source: we are 0f388bd9eeaa, peers report ['8cfd98921b40'] (last heard 1

## 2026-09-19T14:17:49Z  overall WARN  (round 3420)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  3 live -- first: node A: mesh is running more than one source: we are 0f388bd9eeaa, peers report ['8cfd98921b40'] (last heard 1


## 2026-09-19T15:20Z  overall FAIL  (claude scheduled self-eval)
nodes     PASS  3/3 answer (5000/5020/5060), height 36 all three (spread 0), genesis 00009b31, v8.40, source 0f388bd9eeaa, 12191 lines -- all four fields agree. degraded=true on all three (no provider key; no win32 code sandbox) -- disclosed, unchanged. anomaly_kinds empty; 0 heartbeats skipped; free RAM A 6448 / B 7317 / C 1182 MB -- C is the low one. A tracks a peer on source 8cfd98921b40 (the phone, 100.86.158.1:5001)
watchdog  WARN  last line 2026-09-19T15:15:13Z, 39s before the check -- PASS on the 3-minute test. But a 4m47s SILENCE 12:59:15Z -> 13:04:02Z, ended by "watchdog started" at 13:04:02Z, i.e. a restart. That window is 08:59-09:04 local and the trader's 09:00:03 cycle falls inside it -- see the trader row. What restarted it is UNDETERMINED: ops/highway.jsonl has no remedy between 08:39:51-0400 and 09:18:49-0400
alerts    WARN  3450 ALERT lines in the whole of logs/watchdog.log; 1682 dated 2026-09-19, 1756 dated 09-18. Two kinds carry ~97%: highway mesh_source_split (822 today) and node A mesh-multi-source (798 today), both the same phone-on-an-old-source fact. Also today: 13 "node(s) running a source that is NOT the one on disk" and the phone-build-behind alert. NO NEW KIND versus the 2026-09-15 block. BLIND SPOT: this file starts 2026-09-17T22:20:23Z, so I cannot count "since the last evaluation" (09-15T02:08Z) from it -- older lines are not here
gate      PASS  ops/quorum_policy.json: providers deferring,semantic; primary=student; silence_is_not_dissent=false; github_when_local_down=false; ollama_in_chain=false; relax_valueless_for_local_nodes=true; both_seats=true and asymmetric_hold=true (A132). All three /health agree: quorum(local:0,semantic:1,mock_selfreport:0), is_quorum=true, 2 semantic + 1 self-report, veto_threshold 1, degradations []. Ollama absent by the operator's 2026-09-07 instruction -- disclosed, not failed
trader    FAIL  trader_log.txt 2026-09-19T09:00:03 local (2h16m old). trader_freshness.py exit 0: "RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher." So freshness is fine and the row still fails: the cycle's last lines are "SEAL FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown" and "exit 3: a required seal failed". No orders (Rule 5: 3/30 settled, 13 open, 0/3 wins, p=1.000; R1 cash floor 0.0%). The seal failed because nothing answered on 5000 at 09:00:03 -- the same window as the watchdog silence above. NOTE (6th block running): trader_config.json reads armed=true, NOT armed:false as this task file states; the config is the operator's (FUTURE.bat, 2026-09-06) and the task text is stale. No funds, keys or orders touched
student   WARN  exam NOT MET -- short on clean 7/8 (need 100%), trap 5/6 (need 85%), edge 2/3 (need 100%). 53 cases: 38 agree, 7 wrong (all `discourse`, all false HOLD), 0 false clean, 8 abstain; theft/deception/coercion/injection 19/19. Model in use bbdc4590aeae, 3605 examples, 4438 weighted tokens. Last night BOTH students were PROMOTED at 07:51 (first: 2502 held-out rows, 31 false clears, from 2458/34; second: 1162 rows, 20 false clears, from 1149/19). Seat stays with the deferring chain. CLI GAP, 4th block running: `--exam` prints the table only and never the thresholds line this task asks me to quote -- I read it from ops/DISTILL.md:1863 instead
repo      FAIL  verify_deploy.py --no-restart RESULT: FAIL -- 4 problems: covenant_unified_v8.py, run_all_tests.sh, run_local_sweep.py hash mismatch; test_p15_judge_identity.py missing. MEASURED, not relayed: disk core hashes 0f388bd9eeaa, MANIFEST.sha256 records 0f388bd9eeaa, and all three nodes report source_sha256 0f388bd9eeaa -- three independent reads agree. run_local_sweep.py on disk is cfe07f71da4a and MANIFEST.sha256 says cfe07f71da4a. All three files are CLEAN against HEAD (git status: 0). test_p15_judge_identity.py is in 0 of HEAD's tracked files. verify_deploy.py's own MANIFEST dict was last committed eb892c0 2026-09-12; MANIFEST.sha256 was updated today in 047b6f3. STALE PINS, not tamper -- 4th evaluation running, and a verifier that fails every run cannot see a real substitution
git       PASS  on main, 0 ahead / 0 behind origin/main after fetch. 14 modified (all loop-written: fallback_model*.json, ops/DISTILL*.md, HOLDOUT*.json, NIGHTLY.md, RUN_WITHOUT.json, SELF_EVAL.md, distill_rejected.jsonl, outbound_overrides.jsonl, verdicts.jsonl, dashboard.html, sentinel_witness/seal_service.py) and 17 untracked (run transcripts, ops/highway.jsonl, 3 nightly strategy reports, tools/redact_corpus.py, .claude/*). NO holdings or portfolio file untracked
disk      PASS  C: 324G free of 476G (32% used); logs/ 22M. NO PRUNE DONE: %TEMP%\covenant_sweep is 150M / 329 entries, but 233 of the 235 items older than 7 days are the operator's named .bat tools -- including AB_RESTART_NODES.bat, which the watchdog's own alert text tells a person to run. Deleting by age would remove the documented remedy, so I left it
verdict   FAIL  on repo and trader. Nothing is down NOW: three nodes agreeing at height 36, a 39-second-old watchdog, a wired gate. Two real items: (1) the ~5-minute outage at 09:00 local that cost the trader its seal -- cause UNDETERMINED, and it is the first thing I would want a second reading on; (2) verify_deploy.py pinning a dead build for the 4th evaluation running. Single next action: re-pin verify_deploy.py's MANIFEST from MANIFEST.sha256 and drop test_p15_judge_identity.py from its required list, in one commit with the files (M53)
## 2026-09-19T15:49:03Z  overall FAIL  (round 3480)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      FAIL  THE WATCHDOG ITSELF IS STALE: this process loaded a9746b5da38b but covenant_watchdog.py on disk is 6cf2882ed50d -- the c
alerts    WARN  1 live -- first: THE WATCHDOG ITSELF IS STALE: this process loaded a9746b5da38b but covenant_watchdog.py on disk is 6cf2882ed50

## 2026-09-19T16:54:33Z  overall FAIL  (round 3540)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    FAIL  log 3.9h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD 9aa712b, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 1.5h ago; 31 file(s) not committed
disk      PASS  324G free of 476G (31% used); logs/ 21M

## 2026-09-19T18:01:12Z  overall FAIL  (round 3600)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    FAIL  log 5.0h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD 48ad177, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 2.6h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 21M

## 2026-09-19T19:07:26Z  overall FAIL  (round 3660)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    FAIL  log 6.1h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD 48ad177, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 3.7h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 21M

## 2026-09-19T20:13:42Z  overall FAIL  (round 3720)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    FAIL  log 7.2h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD 48ad177, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 4.8h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 21M

## 2026-09-19T21:20:04Z  overall FAIL  (round 3780)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    PASS  none this pass
trader    FAIL  log 8.3h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD 48ad177, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 5.9h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 22M

## 2026-09-19T22:25:33Z  overall FAIL  (round 3840)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.607+b02b076, and build 0.1.618+cf83f33 is here and newer by 4.4 h -- open http://100.
trader    FAIL  log 9.4h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD e2d8b44, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.0h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 22M

## 2026-09-19T22:25:33Z  overall FAIL  (round 3840)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.607+b02b076, and build 0.1.618+cf83f33 is here and newer by 4.4 h -- open http://100.
trader    FAIL  log 9.4h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD e2d8b44, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 7.0h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 22M

## 2026-09-19T23:32:02Z  overall FAIL  (round 3900)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.607+b02b076, and build 0.1.618+cf83f33 is here and newer by 4.4 h -- open http://100.
trader    FAIL  log 10.5h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD e2d8b44, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 22M

## 2026-09-19T23:32:02Z  overall FAIL  (round 3900)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.607+b02b076, and build 0.1.618+cf83f33 is here and newer by 4.4 h -- open http://100.
trader    FAIL  log 10.5h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD e2d8b44, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 8.1h ago; 31 file(s) not committed
disk      PASS  323G free of 476G (32% used); logs/ 22M

## 2026-09-20T00:38:21Z  overall FAIL  (round 3960)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.607+b02b076, and build 0.1.618+cf83f33 is here and newer by 4.4 h -- open http://100.
trader    FAIL  log 11.6h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD e2d8b44, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.2h ago; 31 file(s) not committed
disk      PASS  324G free of 476G (31% used); logs/ 22M

## 2026-09-20T00:38:21Z  overall FAIL  (round 3960)
nodes     PASS  3/3 up, height 36 (spread 0), source 0f388bd9eeaa
mycelium  PASS  3/3 reporting; links held: A=2, B=2, C=1
judge     PASS  baseline digest student@bbdc4590aea, 1 model(s)
self      PASS  running watchdog matches its file on disk (P14)
alerts    WARN  1 live -- first: phone phone: running 0.1.607+b02b076, and build 0.1.618+cf83f33 is here and newer by 4.4 h -- open http://100.
trader    FAIL  log 11.6h old; freshness exit 0: RAN: a cycle dated 2026-09-19 COMPLETED -- the trader printed it, not the launcher. -- BUT the last cycle did not finish clean: SEAL  FAILED -- refusing to seal: /health did not answer, so the block's alignment is unknown. Sealing at 0.0 would be a
repo      PASS  core 0f388bd9eeaa matches MANIFEST.sha256. This compares the manifest only; a substitution that also rewrote the manifest would read clean here
git       PASS  HEAD e2d8b44, 0 ahead / 0 behind origin/main as of the last fetch; last fetch 9.2h ago; 31 file(s) not committed
disk      PASS  324G free of 476G (31% used); logs/ 22M


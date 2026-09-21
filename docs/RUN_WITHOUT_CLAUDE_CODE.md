# Running the covenant without a paid Claude seat

Written 2026-09-21, the night the operator said the paid seat may lapse. It
answers one question with measurements, not hopes: **what keeps running with
no Claude at all, what a free Claude chat can still do, and what stops.**

A free Claude chat has no tools. It cannot open a file, run a command, read
this repository, drive a browser or send mail. It can read what is pasted to
it and answer. So the arrangement is: the machine measures, you carry the
measurement to the chat, the chat reasons, you act. Every step below is that.

## 1. What runs with no Claude involved (measured 2026-09-21)

| runner | what | schedule | where it reports |
|---|---|---|---|
| Windows task `CovenantGuard` | keeps the watchdog alive, which keeps the three nodes alive and runs the highway's self-heal | every 2 minutes | `logs/guard.log`, `logs/watchdog.log`, `ops/SELF_EVAL.md` (report-only blocks) |
| Windows task `CovenantRefineCheck` | the student's refinement check (A127) | every 15 minutes | `logs/refine_check.log` |
| Windows task `CovenantDistill` | the nightly: study, back-audit, distillation, strategy re-validation, then the green check (A163) | daily 03:30 | `ops/strategy_reports/NIGHTLY_<date>.txt`, `ops/SELF_EVAL.md`; the task's last result is `1` when the nightly's own green check failed |
| Windows task `CovenantTrader` | the paper trader; disarmed for RETURN by Rule 5 and the standing validation result | daily 09:00 | `ops/` ledgers; it has never been permitted to trade for return |
| GitHub Actions, public repo | `covenant.yml` (the sweep on Ubuntu) and `judge.yml` (the teacher panel the students learn from) | on push and on schedule | github.com/LAWLESS1987/covenant/actions |
| GitHub Actions, private artifact | `covenant.yml`, the artifact's own sweep | on push and every 2 hours | github.com/LAWLESS1987/covenant-satc/actions |
| the nodes themselves | A/B/C on 5000/5020/5060, gossip, re-validation, the mesh with the phone | always | `/health` on each port, `logs/node*.log` |

None of these calls Claude. They were running before this document and will
run after the seat lapses.

Added the evening of 2026-09-21, the last session before the seat lapsed at
midnight, all inside the runners above and all pinned by suites in the sweep:

- the nightly carries the machine's **own work** to the students before the
  queue is consumed -- every ledger entry and every settled code consensus,
  once each, bounded per night (`covenant_own_work.py`, A207; its state is
  `ops/own_work_state.json`, its rows are in `ops/teacher_queue.jsonl` with
  source `own-work:A<n>`);
- the study reading list is 57 public-domain books, each verified against
  its own title before it is read (`python covenant_study.py --verify`);
  child development, the founders of teaching the child who learns
  differently, psychology, and the philosophers (A206);
- no process of the covenant opens a console window any more, and a node or
  the watchdog outlives whatever shell started it (A204,
  `test_qw1_quiet_everywhere.py`). If a window ever appears, the process that
  owns it is listed by `Get-Process | Where-Object { $_.MainWindowTitle -ne "" }`;
- the wire admits a caller by its key over any road, and the phone has the
  LAN as its second road (A200); the image door judges the prompt, draws in
  about 50 s, and refuses a chat reply sent as a scene (A205).

## 2. What stops when the seat lapses

- The app's daily self-evaluation routine (04:43). Its measurement half is
  already done by the watchdog, which writes the same ledger; what stops is
  the judgment half: a model reading the block and deciding what it means.
- Diagnosis, structural fixes, audits, write-ups: the work this file's memory
  calls "Claude only". With a free chat this work still happens, but you
  carry the evidence in and the fix out by hand.
- Email replies drafted and sent from here. The reply kit in
  `private/outreach/` is written so you can answer by hand, and section 4
  says what to paste to get a draft from a free chat. That folder is never
  published and a reader of this file cannot check it; nothing here rests a
  claim on it.
- Browser automation: posting, reading forum replies, the GitHub access
  page. All of it is a few clicks by you; nothing is lost, only convenience.

## 3. The daily check, by hand, about one minute

```bash
python covenant_one.py --check
```

Green looks like `12 PASS   0 BLOCKED   0 UNKNOWN` and every G-line PASS.
Anything else names the gate and the reason on the line under it; that line
is what you paste into the chat, not a description of it.

Then, when something looks off or once a day:

```bash
python tools/context_pack.py
```

It writes `ops/CONTEXT_PACK.txt`: this commit, the gates as last printed, the
last sweep tally, the newest self-evaluation block, the watchdog's last lines,
the open entries of `docs/KNOWN_ISSUES.md` by title, and the standing method.
Every section names its source file and how old it is, so the chat can see
staleness too. `--private` adds the reply kit and writes to `private/` instead,
which git never sees and which is never published; a reader cannot open it.

Weekly, or before quoting the system as green anywhere:

```bash
python covenant_one.py --all --out ONE_SWEEP.txt
```

About fifteen minutes. The tally at the end is the only green that counts, and
gate G12 turns red by itself when a week passes without one.

## 4. How to use a free Claude chat with it

Start a new chat and paste, in this order:

1. The whole of `ops/CONTEXT_PACK.txt` (or the private one). It begins with a
   banner telling the reader what it is and ends with the standing method, so
   the chat works the way sessions here work: count first, cite only what it
   was shown, name what it cannot see.
2. One line saying what you want: "tell me whether this is green and what to
   run next", or "draft a reply to this email, using only the kit's numbers".
3. For an email reply, paste the incoming mail too. The kit's rule stands:
   nothing goes out without your reading it, and the disclosure line stays.

What the chat cannot do, and will say so if the pack is read: run anything,
see anything not pasted, or know whether a file changed after the pack was
written. When it proposes a command, you run it and paste the output back.

Free-tier limits are real: a long pack uses a good part of a day's allowance.
`--max-kb 40` trims it; the gates and the tally come first and survive the trim.

## 5. What "a fully functional app" would have to carry, and does not yet

The phone app and the PC's agent door (the 3B model, judged and leashed; A147
onward) run the routine: chat, judge, share a node, learn from use. They do not
yet do the judgment work in section 2. To carry it, measured against what
exists on 2026-09-21:

| needed | exists | gap |
|---|---|---|
| read the pack and say what is green | the agent door answers questions over the tree at about ten tokens a second | no suite measures its answers against the transcript; a wrong "green" from it is the failure mode this repository was built to refuse |
| draft an outward reply from the kit's numbers | the app drafts and nothing leaves the device | no guard yet pins that a draft quotes only figures a script printed |
| decide a fix and apply it | the code proposals path exists and refuses every proposal on Windows (no sandbox) | by design; a model that edits its own guards unwatched is the thing the covenant judges, not the thing it is |
| close the students' loop from its own use | done 2026-09-21 (A166): conversations and the phone's AI-app screens go to the teacher's queue, and the nightly carries it to the panel, balanced, once each | none open; the panel and the promotion gate decide what teaches |

The honest order is the same as the phone-app rule already on record: the
pipeline first, then one app build, then the local model doing more. None of
it is a refinement; each is new capability, which by the standing rule waits
for a second operator or your explicit word. This file is what runs meanwhile.

## 6. Two things only you can do, seat or no seat

- Tap the waiting phone build. The watchdog has been proposing it since
  2026-09-20 22:56 and the mesh reports one peer on an older source until then.
- Grant artifact access on GitHub when a researcher sends a username; the
  reply kit has the steps.

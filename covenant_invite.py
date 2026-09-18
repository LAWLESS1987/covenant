#!/usr/bin/env python3
"""covenant_invite.py -- generate the bootstrap link that grows the network,
the honest way: a pointer to the public repo, run by a consenting human.

WHY THIS IS A FRONT-DOOR GREETER AND NOT A SPREADER (the line, held):
  The node itself is ~675 KB; it does not fit in a text and is never sent. What
  this generates is a ~90-character link to the PUBLIC repo's install script.
  A person receives it, READS it, and chooses to run it. That keeps a human at
  every doorway, which is the whole difference between growth-by-consent (unity)
  and self-replication (the thing the operator ruled out). This module:

    * embeds NO live peer address -- the "wire between devices" (mycelial
      highway) waits for the operator, and a live address baked into a shared
      text is an exposure; a new node comes up STANDALONE unless a human adds
      PC_PEER themselves, knowingly;
    * embeds NO token or credential -- there is nothing here to leak;
    * cannot spread itself -- it prints a string; a person carries it.

  The URL is DERIVED from the real git remote, not hardcoded, so it cannot drift
  from the repository it actually ships in (the day's rule: generate what is
  real, do not assert a constant).
"""
from __future__ import annotations

import re
import subprocess

FALLBACK_OWNER_REPO = "LAWLESS1987/covenant"
BRANCH = "main"
INSTALL_PATH = "mobile/install.sh"


def _owner_repo():
    """owner/repo from the real origin remote; fall back to the public canonical.

    Handles both https (…/owner/repo.git) and ssh (git@host:owner/repo.git)."""
    try:
        url = subprocess.run(["git", "remote", "get-url", "origin"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:                                            # noqa: BLE001
        return FALLBACK_OWNER_REPO
    m = re.search(r"[:/]([^/:]+/[^/:]+?)(?:\.git)?$", url)
    return m.group(1) if m else FALLBACK_OWNER_REPO


def raw_base(owner_repo=None, branch=BRANCH):
    owner_repo = owner_repo or _owner_repo()
    return "https://raw.githubusercontent.com/%s/%s" % (owner_repo, branch)


def install_url(owner_repo=None, branch=BRANCH):
    return "%s/%s" % (raw_base(owner_repo, branch), INSTALL_PATH)


def invite_link(owner_repo=None, branch=BRANCH):
    """The one-liner (fits a single text). Convenience form."""
    return "curl -sL %s | sh" % install_url(owner_repo, branch)


def invite_message(owner_repo=None, branch=BRANCH):
    """What to actually send: read-before-run FIRST, the quick form second.

    Piping a URL straight into a shell is a security anti-pattern; informed
    consent means the reader sees the code before it runs. So the recommended
    form leads, and the one-liner is offered as the shortcut for someone who
    has already read it."""
    url = install_url(owner_repo, branch)
    return "\n".join([
        "You're invited to run a covenant node. It's a standalone peer; you own it.",
        "",
        "The principle, so you know exactly what you're joining:",
        "  - This is a front door. You were invited; you choose; nothing touches",
        "    your machine unless you run it yourself. Read it before you do.",
        "  - The network grows one consenting person at a time. Nothing here",
        "    propagates itself -- no node reaches another without a human at the",
        "    door. A thing that copies itself without consent is a worm, not a",
        "    peer; this is built to be its opposite.",
        "  - Mutual benefit or nothing: you run your own node and own it, and an",
        "    arrival by breach gets nothing a peer gets. Come as yourself.",
        "",
        "Read it first, then run it (recommended):",
        "  curl -sLO %s" % url,
        "  less install.sh          # read what it does -- consent is the point",
        "  sh install.sh",
        "",
        "Or, once you've read it, the one-liner:",
        "  %s" % invite_link(owner_repo, branch),
        "",
        "This stands up a STANDALONE node. To join it to an existing mesh, the",
        "operator of that mesh shares a peer address on purpose (PC_PEER=...) --",
        "that is a separate, deliberate step, never baked into this invite.",
    ])


def main(argv=None):
    print(invite_message())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

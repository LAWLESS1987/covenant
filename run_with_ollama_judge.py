#!/usr/bin/env python3
"""run_with_ollama_judge.py -- the launcher's name until 2026-09-12; it is run_node.py now.
Kept one release so a console, watchdog or phone kit still holding the old name finds it.
Same argv, same behaviour: importing run_node applies the policy and registers the seats."""
import run_node  # noqa: F401
if __name__ == "__main__":
    run_node.cov.main()

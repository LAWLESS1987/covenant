"""Offline boundaries for tests of a real watchdog pass, never its daemon.

The node decision and self-evaluation code still runs. Unrelated maintenance
edges are fixtures, and the known subprocess/HTTP/socket boundaries reject
unexpected work instead of letting a stubbed health response trigger it.
"""
from contextlib import ExitStack, contextmanager
import importlib
import socket
import subprocess
import tempfile
import urllib.request
from unittest.mock import patch


@contextmanager
def offline_watchdog_pass(watchdog):
    calls, external = [], []

    def fixture(name, value):
        def invoke(*args, **kwargs):
            calls.append(name)
            return value
        return invoke

    def forbid(name):
        def invoke(*args, **kwargs):
            external.append(name)
            raise RuntimeError("offline watchdog test attempted " + name)
        return invoke

    with ExitStack() as stack:
        directory = stack.enter_context(tempfile.TemporaryDirectory())
        stack.enter_context(patch.object(watchdog, "HERE", directory))
        stack.enter_context(patch.dict(watchdog._self_eval, {"persist": False}))
        for name, value in (
            ("tend_seal_service", "up"),
            ("tend_earn_service", "no grant"),
            ("tend_pending", "nothing pending"),
            ("mycelium", (None, "offline fixture")),
            ("anomalies", (None, "offline fixture")),
            ("push_alert", ("disabled", "offline fixture")),
            ("_student_state", {"digest": "fixture", "served": {}, "loaded": []}),
            ("offline_readings", {"repo": ("PASS", "offline fixture")}),
        ):
            stack.enter_context(patch.object(watchdog, name, fixture(name, value)))
        for module, name, value in (
            ("covenant_daily_plan", "checkin_report", ([], [])),
            ("covenant_daily_plan", "build_report", ([], [])),
            ("covenant_highway", "run_once", ([], [])),
            ("covenant_refine_loop", "tick", {"ran": False, "attempted": False}),
            ("covenant_pause", "report", ([], [])),
            ("covenant_actuator_guide", "status", "offline fixture"),
        ):
            target = importlib.import_module(module)
            label = module + "." + name
            stack.enter_context(patch.object(target, name, fixture(label, value)))
        for target, name, label in (
            (subprocess, "Popen", "process launch"),
            (subprocess, "run", "process run"),
            (urllib.request, "urlopen", "HTTP request"),
            (socket, "create_connection", "socket connection"),
            (socket, "socket", "socket creation"),
        ):
            stack.enter_context(patch.object(target, name, forbid(label)))
        try:
            yield {"calls": calls, "external": external}
        finally:
            if external:
                raise AssertionError("offline watchdog boundary crossed: "
                                     + ", ".join(external))

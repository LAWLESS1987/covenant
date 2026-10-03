"""Bounded reply replay for authenticated conversational requests.

Each door authenticates once BEFORE calling this helper. A lost response can
then be fetched with the same request id without running the model or its work
twice. This is process-local protection: restart and expiry end the record.
Legacy callers without request_id retain the ordinary route behavior.
"""
from __future__ import annotations

import hashlib
import base64
import json
import re
import threading
import time


def authenticated_reply_key(addr, request, who="", how="tailnet"):
    """Call only AFTER admission: distinguish verified public keys at one address."""
    if how == "tailnet":
        if request.headers.get("X-Operator-Signature"):
            try:
                import importlib
                covenant_mycelium = importlib.import_module("covenant_mycelium")
                # The network already admits this request. Verify an optional
                # signature separately to identify the same registered caller
                # over both roads; never trust a public-key header by itself.
                ok, signed_addr, signed_who, signed_how = covenant_mycelium.admit(
                    request, request.get_data() or b"", lambda _addr: False)
                if ok:
                    return authenticated_reply_key(signed_addr, request, signed_who, signed_how)
            except Exception:                                     # noqa: BLE001
                pass
            # A supplied credential cannot become a second, unsigned identity
            # after a bad signature or reused nonce. Unsigned clients still
            # retain their ordinary tailnet admission below.
            return None
        return ("tailnet", addr)
    encoded = request.headers.get("X-Operator-Pubkey", "")
    if encoded:
        # The admission routine has already decoded and verified these bytes.
        # Keep a digest rather than public PEM or request headers in the cache.
        verified_pem = base64.b64decode(encoded).decode("utf-8")
        key_digest = hashlib.sha256("".join(verified_pem.split()).encode("utf-8")).hexdigest()
        return ("signed", key_digest)
    return (how, addr, who)  # fixture/older verifier; still bounded by its admission


class ConversationReplies:
    def __init__(self, capacity=256, retention=600, clock=time.monotonic):
        if capacity < 1 or retention <= 0:
            raise ValueError("reply retention and capacity must be positive")
        self.capacity = capacity
        self.retention = retention
        self.clock = clock
        self._lock = threading.Lock()
        self._rows = {}

    def reply(self, caller, door, body, operation):
        from flask import Response, jsonify, make_response

        request_id = body.get("request_id") if isinstance(body, dict) else None
        if request_id is None:
            return operation()
        if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", request_id):
            return jsonify(status="error", message="invalid conversation request id"), 400
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False,
                                                separators=(",", ":")).encode("utf-8")).digest()
        key = (caller, door, request_id)
        with self._lock:
            now = self.clock()
            self._rows = {k: v for k, v in self._rows.items()
                          if v["response"] is None or now - v["finished"] < self.retention}
            row = self._rows.get(key)
            if row is not None:
                if row["fingerprint"] != fingerprint:
                    return jsonify(status="error", message="this request id belongs to a different conversation turn"), 409
                if row["response"] is None:
                    return jsonify(status="error", in_progress=True,
                                   message="this turn is still running; retry the same request id to retrieve its reply"), 409
                data, status, headers = row["response"]
                return Response(data, status=status, headers=headers)
            # Never evict a pending or unexpired turn to make room: doing so
            # would silently permit its work to run again on a network retry.
            if len(self._rows) >= self.capacity:
                return jsonify(status="error", message="conversation reply memory is full; wait before starting another turn"), 503
            self._rows[key] = {"fingerprint": fingerprint, "response": None, "finished": 0}
        try:
            response = make_response(operation())
            saved = (response.get_data(), response.status_code, list(response.headers))
        except Exception as error:
            # Work may already have happened before an unexpected exception.
            # Remember that failed attempt too, rather than blindly repeat it.
            response = make_response(jsonify(status="error", message="the conversation attempt failed (%s)" % type(error).__name__), 503)
            saved = (response.get_data(), response.status_code, list(response.headers))
        with self._lock:
            self._rows[key]["response"] = saved
            self._rows[key]["finished"] = self.clock()
        return response

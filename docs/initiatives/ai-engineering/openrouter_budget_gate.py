#!/usr/bin/env python3
"""Fail-closed, no-spend OpenRouter provider-enforced key budget preflight.

Only a provider-side key spending limit qualifies. A workflow variable named
MAX_SPEND_USD does NOT enforce spend. Never print key or provider account data.
"""
import json
import math
import os
import sys
import urllib.error
import urllib.request

URL = "https://openrouter.ai/api/v1/key"
MAX_USD = 1.0


def check_data(data):
    if not isinstance(data, dict):
        return {"decision": "STOP", "reason": "invalid_provider_data"}
    # OpenRouter's key endpoint exposes 'limit' and 'limit_remaining'.
    # Boolean is not a valid numeric budget even though bool subclasses int.
    limit, remaining = data.get("limit"), data.get("limit_remaining")
    for value in (limit, remaining):
        if type(value) not in (float, int) or not math.isfinite(value):
            return {"decision": "STOP", "reason": "provider_cap_not_proven"}
    if not 0 < limit <= MAX_USD:
        return {"decision": "STOP", "reason": "provider_limit_outside_pilot"}
    if not 0 < remaining <= MAX_USD or remaining > limit:
        return {"decision": "STOP", "reason": "provider_remaining_outside_pilot"}
    return {"decision": "PASS", "reason": "provider_key_limit_verified",
            "model_invoked": False, "live_execution_authorized": False}


def probe(key, opener=urllib.request.urlopen):
    if not key or not key.startswith("sk-or-"):
        return {"decision": "STOP", "reason": "missing_or_unexpected_key"}
    request = urllib.request.Request(
        URL, method="GET",
        headers={"Authorization": "Bearer " + key, "Accept": "application/json"})
    try:
        with opener(request, timeout=10) as response:
            payload = json.load(response)
        return check_data(payload.get("data") if isinstance(payload, dict) else None)
    except urllib.error.HTTPError as error:
        return {"decision": "STOP", "reason": "http_error", "http_status": error.code}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, TypeError):
        return {"decision": "STOP", "reason": "provider_unavailable"}


def self_test():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self, *args): return b'{"data":{"limit":1.0,"limit_remaining":0.75}}'
    assert check_data({"limit": 1, "limit_remaining": .5})["decision"] == "PASS"
    for values in (
        {}, {"limit": None, "limit_remaining": 1},
        {"limit": 2, "limit_remaining": 1},
        {"limit": 1, "limit_remaining": 2},
        {"limit": 1, "limit_remaining": 0},
        {"limit": True, "limit_remaining": 1},
        {"limit": 1, "limit_remaining": float("nan")},
        {"limit": float("inf"), "limit_remaining": 1},
        {"limit": "1", "limit_remaining": 1},
    ):
        assert check_data(values)["decision"] == "STOP", values
    assert probe("")["decision"] == "STOP"
    result = probe("sk-or-offline-fixture", lambda request, timeout: Response())
    assert result["decision"] == "PASS" and not result["live_execution_authorized"]
    print("PASS: provider budget cap contract, no network or model invocation")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif sys.argv[1:] == ["--live"]:
        verdict = probe(os.environ.get("OPENROUTER_API_KEY", ""))
        print(json.dumps(verdict, sort_keys=True))
        sys.exit(0 if verdict["decision"] == "PASS" else 1)
    else:
        print("Usage: openrouter_budget_gate.py --self-test|--live", file=sys.stderr)
        sys.exit(2)

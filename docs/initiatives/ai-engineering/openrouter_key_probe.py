#!/usr/bin/env python3
"""One-shot, read-only OpenRouter credential probe. No model requests or agent launch.

Never prints the key, account details, credit balance or response body.
Only run in an owner-approved protected environment; do not pass secrets to PR CI.
"""
import json
import os
import sys
import urllib.error
import urllib.request

URL = "https://openrouter.ai/api/v1/key"


def probe(key, opener=urllib.request.urlopen):
    if not key or not key.startswith("sk-or-"):
        return {"status": "STOP", "reason": "missing_or_unexpected_key"}
    request = urllib.request.Request(
        URL,
        headers={"Authorization": "Bearer " + key,
                 "Accept": "application/json",
                 "User-Agent": "openhands-pilot-key-probe/1"},
        method="GET",
    )
    try:
        with opener(request, timeout=10) as response:
            # A credential endpoint is not a model invocation; never print its payload.
            payload = json.load(response)
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), dict):
                return {"status": "STOP", "reason": "unexpected_response"}
            return {"status": "PASS", "reason": "credential_endpoint_responded",
                    "model_invoked": False, "charged_request": False}
    except urllib.error.HTTPError as exc:
        # Do not echo provider error bodies or response headers.
        return {"status": "STOP", "reason": "http_error", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, ValueError, TypeError, OSError):
        return {"status": "STOP", "reason": "endpoint_unavailable_or_invalid"}


def self_test():
    class FakeResponse:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, *args):
            return b'{"data":{"label":"redacted"}}'
    assert probe("")["status"] == "STOP"
    assert probe("not-a-key")["status"] == "STOP"
    def fake_open(request, timeout):
        assert request.get_method() == "GET"
        assert timeout == 10
        return FakeResponse()
    result = probe("sk-or-fake-for-offline-test", fake_open)
    assert result["status"] == "PASS"
    assert "label" not in str(result)
    def invalid_json(request, timeout):
        class BadResponse(FakeResponse):
            def read(self, *args):
                return b"not-json"
        return BadResponse()
    assert probe("sk-or-fake-for-offline-test", invalid_json)["status"] == "STOP"
    def rejected(request, timeout):
        raise urllib.error.HTTPError(URL, 401, "invalid token secret", {}, None)
    rejected_result = probe("sk-or-fake-for-offline-test", rejected)
    assert rejected_result == {"status": "STOP", "reason": "http_error", "http_status": 401}
    assert "secret" not in str(rejected_result)
    print("PASS: offline OpenRouter key-probe contract (no network, no secrets)")


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    elif sys.argv[1:] == ["--live"]:
        result = probe(os.environ.get("OPENROUTER_API_KEY", ""))
        print(json.dumps(result, sort_keys=True))
        sys.exit(0 if result["status"] == "PASS" else 1)
    else:
        print("Usage: openrouter_key_probe.py --self-test|--live", file=sys.stderr)
        sys.exit(2)

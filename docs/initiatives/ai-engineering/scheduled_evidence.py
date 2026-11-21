#!/usr/bin/env python3
"""Read-only hourly GitHub Actions schedule evidence. Never authorizes an agent."""
import argparse
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.request

REPO = "DaniilSydorenko/.github"
WORKFLOWS = ("ai-eng-scheduled-hello-smoke.yml", "ai-eng-haversine-real-test-smoke.yml")
API = "https://api.github.com/repos/" + REPO
MAX_AGE_MINUTES = 150


def github_get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "ai-eng-evidence-v2"}
    if os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
        return json.load(response)


def parse_time(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def inspect(fetch, now):
    report = {"checked_at": now.isoformat(), "workflows": {}, "overall": "UNKNOWN"}
    decisions = []
    for workflow in WORKFLOWS:
        url = API + "/actions/workflows/" + workflow + "/runs?event=schedule&per_page=20"
        try:
            payload = fetch(url)
            runs = payload["workflow_runs"]
            if not isinstance(runs, list):
                raise ValueError("invalid workflow_runs")
            valid = [r for r in runs if isinstance(r, dict) and r.get("event") == "schedule"
                     and str(r.get("path") or "").split("@", 1)[0].endswith("/" + workflow)
                     and r.get("created_at")]
            if not valid:
                item = {"decision": "MISSING", "reason": "no_scheduled_run"}
            else:
                latest = max(valid, key=lambda r: parse_time(r["created_at"]))
                age = (now - parse_time(latest["created_at"])).total_seconds() / 60
                item = {"run_id": latest.get("id"), "created_at": latest["created_at"],
                        "age_minutes": round(age, 1), "status": latest.get("status"),
                        "conclusion": latest.get("conclusion"), "head_sha": latest.get("head_sha"),
                        "url": latest.get("html_url"), "event": "schedule"}
                if age < -5:
                    item.update(decision="UNKNOWN", reason="future_timestamp")
                elif age > MAX_AGE_MINUTES:
                    item.update(decision="STALE", reason="no_recent_scheduled_run")
                elif latest.get("status") != "completed":
                    item.update(decision="PENDING")
                elif latest.get("conclusion") == "success":
                    item.update(decision="PASS")
                else:
                    item.update(decision="FAIL")
        except (urllib.error.URLError, TimeoutError, ValueError, TypeError, KeyError, OSError, AttributeError):
            item = {"decision": "UNKNOWN", "reason": "api_or_payload_error"}
        report["workflows"][workflow] = item
        decisions.append(item["decision"])
    report["overall"] = "PASS" if all(x == "PASS" for x in decisions) else (
        "FAIL" if any(x == "FAIL" for x in decisions) else
        "MISSING" if any(x in ("MISSING", "STALE") for x in decisions) else
        "UNKNOWN" if any(x == "UNKNOWN" for x in decisions) else "PENDING")
    return report


def self_test():
    now = parse_time("2026-11-21T16:40:00Z")
    def response(url):
        workflow = url.split("/workflows/")[1].split("/")[0]
        return {"workflow_runs": [{"id": 123, "event": "schedule",
            "path": ".github/workflows/" + workflow + "@main",
            "created_at": "2026-11-21T16:05:00Z", "status": "completed",
            "conclusion": "success", "head_sha": "a" * 40}]}
    assert inspect(response, now)["overall"] == "PASS"
    assert inspect(lambda url: {"workflow_runs": []}, now)["overall"] == "MISSING"
    assert inspect(lambda url: {"workflow_runs": [
        {"event": "workflow_dispatch", "path": ".github/workflows/" + WORKFLOWS[0],
         "created_at": "2026-11-21T16:05:00Z"}]}, now)["overall"] == "MISSING"
    def failed(url):
        data = response(url)
        data["workflow_runs"][0]["conclusion"] = "failure"
        return data
    assert inspect(failed, now)["overall"] == "FAIL"
    assert inspect(response, now + dt.timedelta(hours=4))["overall"] == "MISSING"
    assert inspect(lambda url: (_ for _ in ()).throw(urllib.error.URLError("offline")), now)["overall"] == "UNKNOWN"
    print("PASS: scheduled evidence fixtures")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    report = inspect(github_get, dt.datetime.now(dt.timezone.utc))
    print(json.dumps(report, sort_keys=True, indent=2))
    # This job reports evidence; unknown/missing/failed schedule must not appear green.
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

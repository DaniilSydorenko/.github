#!/usr/bin/env python3
"""CI helper: run #166-preconditions overlay integration with explicit anti-skip proof."""
from __future__ import annotations

import importlib.util
import sys
import unittest


TESTS = (
    "test_openhands_lease_admission_adapter.AdapterNegativeTests."
    "test_full_shape_ok_still_not_live_authorization",
    "test_openhands_lease_admission_adapter.AdapterNegativeTests."
    "test_wrong_phase_stops_via_preconditions",
)


def main() -> int:
    if importlib.util.find_spec("openhands_164_lease_preconditions") is None:
        print("FAIL: openhands_164_lease_preconditions overlay missing", file=sys.stderr)
        return 1
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in TESTS:
        suite.addTest(loader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        for case, reason in result.skipped:
            print(f"FAIL: skipped {case}: {reason}", file=sys.stderr)
        return 2
    if not result.wasSuccessful():
        return 3
    print(
        "PASS: precondition_overlay_integration",
        f"tests_run={result.testsRun}",
        f"skipped={len(result.skipped)}",
        f"failures={len(result.failures)}",
        f"errors={len(result.errors)}",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
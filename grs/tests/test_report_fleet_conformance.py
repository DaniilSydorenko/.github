"""Regression tests for read-only GRS fleet conformance reporting."""
import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "report_fleet_conformance.py"
spec = importlib.util.spec_from_file_location("fleet_report", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

REGISTRY = {"repositories": [
    {"repository": "owner/one", "grs_class": "platform"},
    {"repository": "owner/two", "grs_class": "knowledge"},
]}


class FleetReportTests(unittest.TestCase):
    def test_missing_evidence_is_unknown(self):
        report = module.build_report(REGISTRY, {})
        self.assertEqual(report["repository_count"], 2)
        self.assertEqual(report["counts"]["manifest"]["UNKNOWN"], 2)
        self.assertEqual(report["counts"]["ci"]["PASS"], 0)

    def test_independent_dimensions(self):
        report = module.build_report(REGISTRY, {"owner/one": {
            "discovery": {"state": "PASS", "source": "registry validation"},
            "manifest": {"state": "FAIL", "source": "404 exact path"},
        }})
        self.assertEqual(report["counts"]["discovery"]["PASS"], 1)
        self.assertEqual(report["counts"]["manifest"]["FAIL"], 1)
        self.assertEqual(report["counts"]["operational"]["UNKNOWN"], 2)

    def test_reject_unsubstantiated_pass(self):
        with self.assertRaises(ValueError):
            module.build_report(REGISTRY, {"owner/one": {"ci": {"state": "PASS"}}})

    def test_reject_unapproved_exception(self):
        with self.assertRaises(ValueError):
            module.build_report(REGISTRY, {"owner/one": {
                "manifest": {"state": "EXCEPTION", "source": "owner discussion"}
            }})

    def test_reject_unknown_repository(self):
        with self.assertRaises(ValueError):
            module.build_report(REGISTRY, {"owner/unknown": {}})


if __name__ == "__main__":
    unittest.main()

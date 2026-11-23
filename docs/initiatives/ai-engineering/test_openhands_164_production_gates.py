"""Production gates must reject env forgery without API evidence."""
from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from openhands_164_production_gates import verify_g3_lease_ruleset, verify_provider_hard_cap


class ProductionGateTests(unittest.TestCase):
    def test_forged_provider_env_rejected(self):
        os.environ["AI_ENG_PROVIDER_CAP_STEP_OK"] = "1"
        try:
            _, err, _ = verify_provider_hard_cap(
                "sk-or-x",
                probe=lambda _k: {"decision": "STOP", "reason": "provider_cap_not_proven"},
            )
            self.assertEqual(err["reason"], "forged_provider_cap_env_rejected")
        finally:
            os.environ.pop("AI_ENG_PROVIDER_CAP_STEP_OK", None)

    def test_provider_pass_ignores_env_optional(self):
        _, err, verdict = verify_provider_hard_cap(
            "sk-or-x",
            probe=lambda _k: {
                "decision": "PASS",
                "reason": "provider_key_limit_verified",
                "live_execution_authorized": False,
            },
        )
        self.assertIsNone(err)
        self.assertEqual(verdict["decision"], "PASS")

    def test_forged_g3_env_rejected(self):
        os.environ["AI_ENG_G3_RULESET_ATTESTED"] = "1"
        os.environ["AI_ENG_WRITER_APP_ID"] = "5535339"
        try:
            with patch(
                "openhands_164_production_gates.public_readonly_probe",
                return_value={"status": "STOP", "reason": "disabled_ruleset"},
            ):
                err = verify_g3_lease_ruleset("tok", transport=lambda *a: {})
            self.assertEqual(err["reason"], "forged_g3_ruleset_env_rejected")
        finally:
            os.environ.pop("AI_ENG_G3_RULESET_ATTESTED", None)
            os.environ.pop("AI_ENG_WRITER_APP_ID", None)

    def test_g3_requires_authenticated_candidate_not_env(self):
        os.environ["AI_ENG_WRITER_APP_ID"] = "5535339"
        try:
            with patch(
                "openhands_164_production_gates.public_readonly_probe",
                return_value={"status": "STOP", "reason": "lease_branch_unprotected"},
            ):
                err = verify_g3_lease_ruleset("tok", transport=lambda *a: {})
            self.assertEqual(err["reason"], "g3_immutable_ruleset_not_proven")
        finally:
            os.environ.pop("AI_ENG_WRITER_APP_ID", None)


if __name__ == "__main__":
    unittest.main()
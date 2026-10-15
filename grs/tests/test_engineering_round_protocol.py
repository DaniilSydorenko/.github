"""Regression checks for the HQ engineering round protocol.

These tests verify document integrity only. They do not approve Governance v1,
enforce policy in domain repositories, or prove a live end-to-end pilot.
"""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
ROADMAP = ROOT / "reports/github-hq/ROADMAP-LIVE.md"
ACTIVE_MILESTONES = {"M0", "M1", "M2", "M3", "M4", "M5", "M8", "M9", "M10"}
DEFERRED_MILESTONES = set()  # Deferred M6/M7 remain in Git history, not active roadmap
GOVERNANCE_MILESTONES = {f"GOV-M{i:02d}" for i in range(1, 9)}


def milestone_rows(content: str, governance: bool) -> dict[str, tuple[str, int]]:
    """Read only the existing canonical milestone rows; ignore child tasks."""
    if governance:
        section = content.split("## GOV — Engineering Governance v1", 1)[1]
        pattern = r"(?m)^\| (GOV-M0[1-8]) — [^|\n]+ \| ([^|\n]+) \| ([0-9]+)% \|$"
    else:
        section = content.split("## M0 — Final Forensic Audit", 1)[1].split(
            "## GOV — Engineering Governance v1", 1
        )[0]
        pattern = r"(?m)^\| (M(?:10|[0-9])) — [^|\n]+ \| ([^|\n]+) \| ([0-9]+)% \|$"
    matches = re.findall(pattern, section)
    rows = {key: (color.strip(), int(percent)) for key, color, percent in matches}
    if len(rows) != len(matches):
        raise ValueError("duplicate canonical milestone rows")
    return rows


def claimed_closure(content: str, label: str) -> tuple[int, int, float]:
    pattern = (
        r"(?m)^\| \*\*" + re.escape(label)
        + r"\*\* \| \*\*([0-9]+)/([0-9]+) = ([0-9]+(?:\.[0-9]+)?)%\*\* \|"
    )
    matches = re.findall(pattern, content)
    if len(matches) != 1:
        raise ValueError(f"expected one canonical scoreboard row for {label}")
    numerator, denominator, percentage = matches[0]
    return int(numerator), int(denominator), float(percentage)


PROTOCOL = ROOT / "reports/github-hq/ENGINEERING-ROUND-PROTOCOL.md"
STAGES = (
    "DISCOVERY",
    "RECONCILIATION",
    "PLANNING",
    "DESIGN",
    "IMPLEMENTATION",
    "VALIDATION",
    "PR REVIEW",
    "EXACT-HEAD CI",
    "INTEGRATION OR BLOCKED",
    "POST-INTEGRATION AUDIT",
    "ROADMAP SYNC",
    "HANDOFF",
)


class EngineeringRoundProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = PROTOCOL.read_text(encoding="utf-8")

    def test_exactly_twelve_ordered_stages(self):
        numbered = re.findall(r"(?m)^([0-9]+)[.] [*][*]([A-Z][A-Z -]+)[*][*]", self.content)
        self.assertEqual(
            [(str(i), name) for i, name in enumerate(STAGES, start=1)],
            numbered,
        )

    def test_required_safety_boundaries(self):
        for phrase in (
            "NON-ENFORCING",
            "owner gate #56",
            "all open PRs",
            "changed-file",
            "UNKNOWN",
            "exact",
            "default branch",
            "No new DB",
            "no percent inflation",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), self.content.lower())

    def test_finish_first_keeps_existing_authority_and_stop_conditions(self):
        boundaries = (ROOT / "reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md").read_text(encoding="utf-8")
        for requirement in (
            "Finish-first closeout contract",
            "current-run-explicit-authorization",
            "standing owner authorization",
            "owner-authored PRs",
            "Class C",
            "no new status database",
            "Two equivalent failures",
            "default-branch evidence",
            "Stop when finished",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement.lower(), boundaries.lower())
        for requirement in (
            "FINISH-FIRST",
            "OWNER_DECISION",
            "EXTERNAL_BLOCKED",
            "ACCEPTED",
            "stop equivalent retries",
            "synchronous HQ cannot inherit it",
            "no parallel policy",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement.lower(), self.content.lower())

    def test_existing_merge_safety_explains_standing_permission_without_expanding_it(self):
        policy = (ROOT / "governance/AUTOPILOT-MERGE-SAFETY.md").read_text(encoding="utf-8")
        for phrase in (
            "Existing standing Class A/B authorization",
            "already granted, bounded",
            "fresh current-run",
            "exact unchanged head SHA",
            "non-Draft status",
            "owner-authored PRs",
            "Class C changes",
            "default deny",
            "issue #56",
            "no additional merge-policy file",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), policy.lower())

    def test_pilot_does_not_claim_acceptance(self):
        self.assertIn("Pilot acceptance checklist", self.content)
        self.assertIn("**not** a second task-status store", self.content)


class RoadmapAcceptanceScoreTests(unittest.TestCase):
    """Prevent misleading milestone score changes without changing global GRS rules."""

    @classmethod
    def setUpClass(cls):
        cls.roadmap = ROADMAP.read_text(encoding="utf-8")

    def assert_score_reconciles(self, content: str) -> None:
        git = milestone_rows(content, governance=False)
        gov = milestone_rows(content, governance=True)
        self.assertEqual(set(git), ACTIVE_MILESTONES | DEFERRED_MILESTONES)
        self.assertEqual(set(gov), GOVERNANCE_MILESTONES)

        for key, (color, percent) in {**git, **gov}.items():
            with self.subTest(milestone=key):
                self.assertGreaterEqual(percent, 0)
                self.assertLessEqual(percent, 100)
                if percent == 100:
                    self.assertEqual(color, "🟢")
                else:
                    self.assertNotEqual(color, "🟢")

        for label, rows in (
            ("Current GitHub scope — full milestone closure",
             [git[key] for key in sorted(ACTIVE_MILESTONES)]),
            ("Governance v1 — full milestone closure",
             [gov[key] for key in sorted(GOVERNANCE_MILESTONES)]),
        ):
            completed = sum(percent == 100 for _, percent in rows)
            claimed, total, displayed = claimed_closure(content, label)
            self.assertEqual((claimed, total), (completed, len(rows)), label)
            self.assertAlmostEqual(displayed, 100 * completed / len(rows), places=1)

    def test_reported_closeout_ratios_match_canonical_milestones(self):
        self.assert_score_reconciles(self.roadmap)

    def test_m1_risk_acceptance_keeps_machine_readable_score(self):
        milestones = milestone_rows(self.roadmap, governance=False)
        self.assertEqual(milestones["M1"], ("🟢", 100))
        self.assertIn("original portfolio Maps key matched exactly", self.roadmap)
        self.assertIn("owner risk acceptance", self.roadmap)
        self.assertIn("7/9 = 77.8%", self.roadmap)

    def test_roadmap_only_changes_trigger_grs_exact_head_ci(self):
        # Roadmap limits and milestone integrity are checked in this suite.
        # The workflow must actually run this suite when only the roadmap changes.
        workflow = (ROOT / ".github/workflows/grs-control-plane.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("  pull_request:", workflow)
        self.assertIn("  push:", workflow)
        pull, push = workflow.split("  push:", 1)
        required_path = '"reports/github-hq/ROADMAP-LIVE.md"'
        self.assertIn(required_path, pull)
        self.assertIn(required_path, push)

    def test_hq_authority_and_round_protocol_changes_trigger_grs_ci(self):
        # Both files are tested here, so either edited alone must start GRS CI
        # on pull requests and main. Do not silently skip required validation.
        workflow = (ROOT / ".github/workflows/grs-control-plane.yml").read_text(
            encoding="utf-8"
        )
        pull, push = workflow.split("  push:", 1)
        for path in (
            "reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md",
            "reports/github-hq/ENGINEERING-ROUND-PROTOCOL.md",
        ):
            for event in (pull, push):
                with self.subTest(path=path):
                    self.assertIn(f'"{path}"', event)

    def test_live_roadmap_is_compact_with_immutable_history_link(self):
        self.assertLessEqual(len(self.roadmap.splitlines()), 150)
        self.assertLessEqual(len(self.roadmap.encode("utf-8")), 15 * 1024)
        self.assertIn(
            "blob/37dde39e6311f4c3176f156f8ed2a49ca9cf7fa2/"
            "reports/github-hq/ROADMAP-LIVE.md",
            self.roadmap,
        )
        self.assertIn("M4 stays 66% with its original scope", self.roadmap)
        self.assertIn("owner gate #56", self.roadmap.lower())
        self.assertIn("Infrastructure Reset v1", self.roadmap)

    def test_reset_preserves_owner_and_domain_authority_boundaries(self):
        boundaries = (
            ROOT / "reports/github-hq/HQ-AUTOPILOT-BOUNDARIES.md"
        ).read_text(encoding="utf-8")
        for required in (
            "Infrastructure readiness does not depend on domain product",
            "No new C01–C07 binding enforcement",
            "No change to M4's existing scope",
            "do not transfer merge authority to synchronous HQ",
            "150 lines / 15 KiB maximum",
        ):
            with self.subTest(required=required):
                self.assertIn(required.lower(), boundaries.lower())

    def test_inflated_headline_fails_score_reconciliation(self):
        label = "Current GitHub scope — full milestone closure"
        declared = claimed_closure(self.roadmap, label)
        current = (
            f"| **{label}** | **{declared[0]}/{declared[1]} = "
            f"{declared[2]:.1f}%** |"
        )
        inflated = current.replace(
            f"{declared[0]}/{declared[1]}",
            f"{declared[0] + 1}/{declared[1]}",
            1,
        )
        poisoned = self.roadmap.replace(current, inflated, 1)
        self.assertNotEqual(poisoned, self.roadmap)
        with self.assertRaises(AssertionError):
            self.assert_score_reconciles(poisoned)

    def test_unearned_milestone_promotion_fails_score_reconciliation(self):
        active = milestone_rows(self.roadmap, governance=False)
        unfinished = [
            key for key in sorted(ACTIVE_MILESTONES)
            if active[key][1] < 100
        ]
        if not unfinished:
            self.skipTest("all active milestones are already complete")
        key = unfinished[0]
        section = self.roadmap.split(f"## {key} — ", 1)[1]
        original_row = re.search(
            r"(?m)^\| " + re.escape(key) + r" — [^|\n]+ \| [^|\n]+ \| [0-9]+% \|$",
            section,
        )
        self.assertIsNotNone(original_row)
        promoted_row = re.sub(
            r"\| [^|\n]+ \| [0-9]+% \|$",
            "| 🟢 | 100% |",
            original_row.group(0),
        )
        poisoned = self.roadmap.replace(original_row.group(0), promoted_row, 1)
        self.assertNotEqual(poisoned, self.roadmap)
        with self.assertRaises(AssertionError):
            self.assert_score_reconciles(poisoned)


if __name__ == "__main__":
    unittest.main()

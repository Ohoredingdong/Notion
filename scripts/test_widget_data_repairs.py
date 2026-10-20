"""Regression tests for data publication races and official-table failure gates."""
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import publish_widget_data as publisher
import update_mortgage_rates as mortgage
import update_real_estate_pulse as reb
import run_real_estate_pulse_update as runner
from bs4 import BeautifulSoup


def command(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.remote = self.root / "remote.git"
        command(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.a, self.b = self.root / "a", self.root / "b"
        command(self.root, "clone", str(self.remote), str(self.a))
        command(self.a, "config", "user.name", "Regression Test")
        command(self.a, "config", "user.email", "test@example.invalid")
        self.write(self.a, "a.json", "2026-01-01T00:00:00Z", 1)
        self.write(self.a, "b.json", "2026-01-01T00:00:00Z", 1)
        command(self.a, "add", ".")
        command(self.a, "commit", "-m", "initial")
        command(self.a, "push", "origin", "main")
        command(self.root, "clone", str(self.remote), str(self.b))
        command(self.b, "config", "user.name", "Other Widget")
        command(self.b, "config", "user.email", "other@example.invalid")

    def write(self, root, name, stamp, value):
        (root / name).write_text(json.dumps({"generated_at": stamp, "value": value}))

    def remote_json(self, name):
        return json.loads(command(self.remote, "show", "main:" + name))

    def test_real_push_race_preserves_both_widgets(self):
        self.write(self.a, "a.json", "2026-01-02T00:00:00Z", 2)
        original_git, raced = publisher.git, False

        def race(root, *args, **kwargs):
            nonlocal raced
            if args[:1] == ("push",) and not raced:
                raced = True
                self.write(self.b, "b.json", "2026-01-03T00:00:00Z", 3)
                command(self.b, "add", "b.json")
                command(self.b, "commit", "-m", "parallel widget")
                command(self.b, "push", "origin", "main")
            return original_git(root, *args, **kwargs)

        with patch.object(publisher, "git", side_effect=race), patch.object(publisher.time, "sleep"):
            publisher.publish(self.a, ["a.json"], "publish A")
        self.assertTrue(raced)
        self.assertEqual(self.remote_json("a.json")["value"], 2)
        self.assertEqual(self.remote_json("b.json")["value"], 3)

    def test_older_snapshot_cannot_replace_newer_same_file(self):
        self.write(self.a, "a.json", "2026-01-02T00:00:00Z", 2)
        self.write(self.b, "a.json", "2026-01-03T00:00:00Z", 3)
        command(self.b, "add", "a.json")
        command(self.b, "commit", "-m", "newer A")
        command(self.b, "push", "origin", "main")
        publisher.publish(self.a, ["a.json"], "older A")
        self.assertEqual(self.remote_json("a.json")["value"], 3)


class OfficialDataTests(unittest.TestCase):
    def test_bok_rowspan_year_is_preserved(self):
        soup = BeautifulSoup('<table><tr><td rowspan="2">2025</td><td>05월 29일</td><td>2.50</td></tr><tr><td>02월 25일</td><td>2.75</td></tr></table>', "html.parser")
        result = mortgage.collect_bok(soup)
        self.assertEqual(result["changed_at"], "2025-05-29")
        self.assertEqual(result["previous_changed_at"], "2025-02-25")
        self.assertEqual(result["value"], 2.5)

    def test_missing_cofix_cells_are_not_filled_with_zero(self):
        soup = BeautifulSoup('<table><tr><td>2025/10/15</td><td>2025/09</td><td>3.4</td><td>-</td><td>2.8</td></tr></table>', "html.parser")
        with self.assertRaises(ValueError):
            mortgage.collect_cofix(soup)

    def test_reb_data_id_board_link_is_resolved(self):
        result = reb.release_candidates('<a href="javascript:" data-id="12345">주간아파트가격동향(20251013기준)</a>')
        self.assertEqual(result, [("20251013", "https://www.reb.or.kr/reb/na/ntt/selectNttInfo.do?mi=9565&nttSn=12345")])

    def test_reb_wrong_week_and_partial_regions_fail(self):
        header = "지역\n누계\n'25년 '26년 9.7 9.14 9.21 9.28 10.5 10.12\n"
        table = header + "\n".join(name + " 0.10 0.20 0.01 0.02 0.03 0.04 0.05 0.06" for name in reb.REGIONS)
        values, previous = reb.parse_appendix_table(table, "20261012")
        self.assertEqual(len(values), 16)
        self.assertEqual(values["서울"], .06)
        self.assertEqual(previous["서울"], .05)
        with self.assertRaises(RuntimeError):
            reb.parse_appendix_table(table, "20261019")
        with self.assertRaises(RuntimeError):
            reb.parse_appendix_table(table.replace("제주 ", "알수없는지역 "), "20261012")

    def test_reb_failure_preserves_exact_old_data_and_reports_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            output, health = Path(tmp) / "data.json", Path(tmp) / "health.json"
            original = '{"asOf":"2026-08-24","regions":[]}\n'
            output.write_text(original)
            with patch.object(runner, "OUT", output), patch.object(runner, "HEALTH", health), patch.object(reb, "collect", side_effect=RuntimeError("source offline")):
                self.assertFalse(runner.refresh())
            self.assertEqual(output.read_text(), original)
            self.assertEqual(json.loads(health.read_text())["status"], "stale")


if __name__ == "__main__":
    unittest.main(verbosity=2)

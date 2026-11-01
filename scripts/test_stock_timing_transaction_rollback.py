"""Synthetic-only, fail-closed transactional publication fault injection.

No market history, model training, exchange connection, notifications or orders.
"""
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import tempfile
import unittest

import stock_forecast_autopilot as autopilot

FROZEN = datetime(2026, 11, 1, 6, 20, tzinfo=timezone.utc)
SYMBOL = ("SYNTH", "Synthetic-only", "US")


def synthetic_pipeline(root, processor):
    # One collected synthetic response is required by the cycle gate.
    processor(SYMBOL, "daily")
    for name in autopilot.CORE_OUTPUTS:
        path = root / name
        if name.endswith(".jsonl") and not path.exists():
            path.write_text("")
    autopilot.write(root / "stock-direction-forecast.json",
                    {"records": [], "marker": "new_synthetic_report"})
    autopilot.write(root / "stock-forecast-learning-state.json",
                    {"training_updates": 0})
    autopilot.write(root / "stock-forecast-learning.json",
                    {"overall": {"samples": 0, "correct": 0},
                     "learning": {"training_updates": 0}})


class RecoverableCopyFailureTests(unittest.TestCase):
    def test_later_partial_copy_error_restores_earlier_and_inflight_original_bytes(self):
        with tempfile.TemporaryDirectory() as dirname:
            root = Path(dirname)
            previous = {
                "stock-direction-forecast.json": b'{"marker":"old_original","records":[]}' + b"\n",
                "stock-forecast-ledger.jsonl": b'{"id":"original_synthetic_row"}' + b"\n",
            }
            for name, content in previous.items():
                (root / name).write_bytes(content)

            original_copy = autopilot.shutil.copy2
            injected = {"count": 0}

            def fail_during_second_destination(src, dst, *args, **kwargs):
                if Path(dst) == root / "stock-forecast-ledger.jsonl":
                    injected["count"] += 1
                    (root / "stock-forecast-ledger.jsonl").write_bytes(
                        b'{"id":"partially_written')
                    raise OSError("synthetic_mid_copy_io_failure")
                return original_copy(src, dst, *args, **kwargs)

            synthetic_forecast_module = SimpleNamespace(
                process=lambda *_: ({
                    "symbol": "SYNTH", "market": "US", "mode": "daily",
                    "status": "no_call",
                    "reason": "insufficient_regular_session_time",
                    "observed_until": FROZEN.isoformat(),
                    "received_at": FROZEN.isoformat(),
                }, object()))
            synthetic_cascade_module = SimpleNamespace(
                RECIPE={"name": "movement_then_direction", "synthetic_only": True})

            with patch.dict(sys.modules, {
                "run_stock_forecasts": synthetic_forecast_module,
                "stock_forecast_cascade": synthetic_cascade_module,
            }), patch.object(
                autopilot, "verify_stage",
                return_value={"status": "ledger_arithmetic_consistent",
                              "scored": 0, "correct": 0}
            ), patch.object(
                autopilot.shutil, "copy2", side_effect=fail_during_second_destination
            ):
                with self.assertRaisesRegex(OSError, "synthetic_mid_copy_io_failure"):
                    autopilot.run(
                        root=root, pipeline=synthetic_pipeline,
                        clock=lambda: FROZEN)

            self.assertEqual(injected["count"], 1)
            for name, content in previous.items():
                self.assertEqual(
                    (root / name).read_bytes(), content,
                    f"An original output was not restored: {name}")
            self.assertEqual(
                autopilot.read(root, autopilot.REPORT, {})["status"],
                "cycle_rejected")


if __name__ == "__main__":
    unittest.main()

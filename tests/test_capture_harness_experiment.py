import contextlib
import io
import unittest

from scripts.capture_harness_experiment import PROMPT, capture
from test_harness_engine import FakeRouter


class CaptureExperimentTests(unittest.IsolatedAsyncioTestCase):
    async def test_captures_generated_text_and_decisions(self) -> None:
        records = []
        with contextlib.redirect_stdout(io.StringIO()):
            await capture(FakeRouter(), "test", 1, PROMPT, records.append)
        self.assertEqual(len(records), 1)
        events = records[0]["events"]
        self.assertTrue(any(event["event"] == "generated_text" for event in events))
        self.assertTrue(any(event["event"] == "compose" for event in events))
        self.assertEqual(events[-1]["event"], "completed")

    async def test_records_failure_without_claiming_completion(self) -> None:
        class FailingRouter:
            async def stream_chat(self, *args, **kwargs):
                raise RuntimeError("model unavailable")
                yield  # pragma: no cover

        records = []
        with contextlib.redirect_stdout(io.StringIO()):
            await capture(FailingRouter(), "test", 1, PROMPT, records.append)
        self.assertEqual(records[0]["events"][-1]["event"], "capture_error")
        self.assertEqual(records[0]["events"][-1]["data"]["message"], "model unavailable")


if __name__ == "__main__":
    unittest.main()

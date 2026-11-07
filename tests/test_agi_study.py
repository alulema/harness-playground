import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import agi_study
from test_harness_engine import FakeRouter


MODEL_INFO = {
    "ollama_version": "test",
    "models": {"test-model": {"name": "test-model", "digest": "test-digest"}},
}


class StudyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.dev_task = self.root / "dev-task.json"
        self.dev_task.write_text(json.dumps({
            "domain": "WorkBuddy", "prompt": "Development task only", "id": "dev"
        }))
        self.heldout = self.root / "heldout.json"
        self.heldout.write_text(json.dumps([{"id": "secret", "prompt": "Held-out task only"}]))
        for name, value in (("DEVELOPMENT", self.dev_task), ("HELDOUT", self.heldout)):
            patcher = patch.object(agi_study, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

        async def fake_metadata(_router):
            return MODEL_INFO

        patcher = patch.object(agi_study, "metadata", fake_metadata)
        patcher.start()
        self.addCleanup(patcher.stop)

    async def test_development_freezes_before_blinded_holdout(self) -> None:
        router = FakeRouter()
        dev_path = self.root / "development.json"
        dev = await agi_study.develop(router, dev_path, ["test-model"])
        self.assertEqual(dev["runs"][0]["status"], "completed")
        for request in router.requests:
            self.assertNotIn("Held-out task only", json.dumps(request))
        router.requests.clear()
        raw, blind, key = [self.root / name for name in ("raw.json", "blind.json", "key.json")]
        result = await agi_study.evaluate(router, dev_path, raw, blind, key, 2)
        self.assertEqual(len(result["pairs"]), 2)
        self.assertEqual(len(router.requests), 4)
        system_prompts = [request["messages"][0]["content"] for request in router.requests]
        self.assertEqual(sum("State what is known" in prompt for prompt in system_prompts), 2)
        packet = json.loads(blind.read_text())
        mapping = json.loads(key.read_text())
        self.assertNotIn("test-model", blind.read_text())
        self.assertNotIn('"candidate"', blind.read_text())
        self.assertEqual({pair["id"] for pair in packet["pairs"]}, {pair["id"] for pair in mapping["pairs"]})
        for pair in result["pairs"]:
            self.assertEqual(set(pair["generation_order"]), {"base", "candidate"})
            self.assertEqual(pair["responses"]["candidate"]["text"], "optimized answer")
            self.assertEqual(pair["responses"]["base"]["text"], "base answer")
        with self.assertRaises(FileExistsError):
            await agi_study.evaluate(router, dev_path, raw, blind, key, 1)

    async def test_failed_or_unaccepted_development_cannot_be_evaluated(self) -> None:
        router = FakeRouter()
        dev_path = self.root / "development.json"
        dev = await agi_study.develop(router, dev_path, ["test-model"])
        dev["runs"][0]["status"] = "error"
        dev_path.write_text(json.dumps(dev))
        with self.assertRaisesRegex(ValueError, "No completed development"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 1)

    async def test_development_task_change_invalidates_evaluation(self) -> None:
        router = FakeRouter()
        dev_path = self.root / "development.json"
        await agi_study.develop(router, dev_path, ["test-model"])
        self.dev_task.write_text("{}")
        with self.assertRaisesRegex(ValueError, "development task changed"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 1)

    async def test_heldout_task_change_invalidates_evaluation(self) -> None:
        router = FakeRouter()
        dev_path = self.root / "development.json"
        dev = await agi_study.develop(router, dev_path, ["test-model"])
        self.assertEqual(dev["heldout_task_sha256"], agi_study.sha256(self.heldout))
        self.heldout.write_text("[]")
        with self.assertRaisesRegex(ValueError, "held-out tasks.*changed"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 1)

    async def test_missing_heldout_freeze_invalidates_evaluation(self) -> None:
        router = FakeRouter()
        dev_path = self.root / "development.json"
        dev = await agi_study.develop(router, dev_path, ["test-model"])
        del dev["heldout_task_sha256"]
        dev_path.write_text(json.dumps(dev))
        with self.assertRaisesRegex(ValueError, "held-out tasks were not frozen"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 1)

    async def test_configured_study_freezes_protocol_and_repetitions(self) -> None:
        router = FakeRouter()
        protocol = self.root / "protocol.md"
        protocol.write_text("Protocol version one")
        config_path = self.root / "config.json"
        config_path.write_text(json.dumps({
            "study_id": "test-v2", "development_task": str(self.dev_task),
            "heldout_tasks": str(self.heldout), "protocol": str(protocol),
            "models": ["test-model"], "repetitions": 2,
        }))
        dev_path = self.root / "development.json"
        dev = await agi_study.develop(router, dev_path, ["test-model"], config_path)
        self.assertEqual(dev["study_id"], "test-v2")
        with self.assertRaisesRegex(ValueError, "Repetitions must match"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 1, config_path)
        protocol.write_text("Protocol version two")
        with self.assertRaisesRegex(ValueError, "protocol or implementation changed"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 2, config_path)
        with self.assertRaisesRegex(ValueError, "configuration is required"):
            await agi_study.evaluate(router, dev_path, self.root / "raw", self.root / "blind", self.root / "key", 2)


if __name__ == "__main__":
    unittest.main()

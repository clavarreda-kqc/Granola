import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("granola_server", Path(__file__).parents[1] / "server.py")
server = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(server)


def valid_metadata():
    return {
        "speaker_id": "hablante_001",
        "dialect": "central",
        "municipality": "Tecpán",
        "duration_seconds": 3.25,
        "recorded_at": "2026-09-20T18:00:00Z",
        "consent": {
            "process_for_notes": True,
            "retain_audio": True,
            "asr_training": False,
            "tts_voice_training": False,
            "confirmation_method": "oral_recorded",
            "form_version": "consent-v0.1-draft",
        },
    }


class MetadataTests(unittest.TestCase):
    def test_accepts_explicit_independent_consent(self):
        record = server.validate_metadata(valid_metadata())
        self.assertFalse(record["consent"]["asr_training"])
        self.assertFalse(record["consent"]["tts_voice_training"])

    def test_rejects_unknown_dialect(self):
        data = valid_metadata(); data["dialect"] = "unknown"
        with self.assertRaisesRegex(ValueError, "seis variantes"):
            server.validate_metadata(data)

    def test_rejects_implicit_consent(self):
        data = valid_metadata(); del data["consent"]["tts_voice_training"]
        with self.assertRaisesRegex(ValueError, "booleanos explícitos"):
            server.validate_metadata(data)

    def test_saves_audio_outside_repo_manifest_examples(self):
        with tempfile.TemporaryDirectory() as temp:
            server.DATA_DIR = Path(temp); server.AUDIO_DIR = Path(temp) / "recordings"; server.MANIFEST = Path(temp) / "recordings.jsonl"
            saved = server.save_recording(valid_metadata(), b"synthetic-audio", "audio/webm")
            self.assertTrue((Path(temp) / saved["audio_path"]).exists())
            line = json.loads(server.MANIFEST.read_text())
            self.assertEqual(line["recording_id"], saved["recording_id"])
            self.assertEqual(line["consent_status"], "active")


if __name__ == "__main__":
    unittest.main()

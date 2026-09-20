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

class ConsentLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        server.DATA_DIR = Path(self.temp.name)
        server.AUDIO_DIR = server.DATA_DIR / "recordings"
        server.MANIFEST = server.DATA_DIR / "recordings.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def save(self, speaker="hablante_001", asr=True, tts=True):
        data = valid_metadata(); data["speaker_id"] = speaker
        data["consent"]["asr_training"] = asr; data["consent"]["tts_voice_training"] = tts
        return server.save_recording(data, b"synthetic-audio", "audio/webm")

    def test_withdrawal_is_recorded_and_excluded_from_all_exports(self):
        self.save()
        event = server.change_consent({"speaker_id": "hablante_001", "asr_training": False, "tts_voice_training": False})
        self.assertEqual(event["consent_status"], "withdrawn")
        self.assertEqual([], server.export_records("asr", server.DATA_DIR / "asr.jsonl"))
        self.assertEqual([], server.export_records("tts", server.DATA_DIR / "tts.jsonl"))

    def test_restriction_is_independent_by_purpose(self):
        self.save()
        server.change_consent({"speaker_id": "hablante_001", "tts_voice_training": False})
        self.assertEqual(1, len(server.export_records("asr", server.DATA_DIR / "asr.jsonl")))
        self.assertEqual([], server.export_records("tts", server.DATA_DIR / "tts.jsonl"))

    def test_export_never_adds_recording_without_original_opt_in(self):
        self.save(asr=False, tts=True)
        self.assertEqual([], server.export_records("asr", server.DATA_DIR / "asr.jsonl"))

    def test_admin_view_shows_effective_flags(self):
        self.save(speaker="safe-speaker")
        server.change_consent({"speaker_id": "safe-speaker", "asr_training": False})
        page = server.admin_html().decode()
        self.assertIn("safe-speaker", page)
        self.assertIn("Estado de consentimiento", page)


if __name__ == "__main__":
    unittest.main()

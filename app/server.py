#!/usr/bin/env python3
"""Servidor local mínimo para captura de audio y metadatos consentidos."""
from __future__ import annotations

import cgi
import json
import os
import re
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "app" / "web"
DATA_DIR = Path(os.environ.get("GRANOLA_DATA_DIR", ROOT / "data" / "local"))
AUDIO_DIR = DATA_DIR / "recordings"
MANIFEST = DATA_DIR / "recordings.jsonl"

DIALECTS = {
    "central",
    "santa_maria_de_jesus",
    "santo_domingo_xenacoj",
    "south_central",
    "western",
    "yepocapa",
}


def validate_metadata(raw: dict) -> dict:
    """Valida y normaliza el manifiesto que acompaña a una grabación."""
    required = ("speaker_id", "dialect", "municipality", "duration_seconds", "recorded_at", "consent")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"Faltan campos: {', '.join(missing)}")

    speaker_id = str(raw["speaker_id"]).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,64}", speaker_id):
        raise ValueError("speaker_id debe ser un seudónimo de 2-64 caracteres (letras, números, _ o -)")
    if raw["dialect"] not in DIALECTS:
        raise ValueError("dialect no es una de las seis variantes MMS")
    municipality = str(raw["municipality"]).strip()
    if not municipality or len(municipality) > 100:
        raise ValueError("municipality es obligatorio y debe tener máximo 100 caracteres")
    try:
        duration = round(float(raw["duration_seconds"]), 3)
    except (TypeError, ValueError) as exc:
        raise ValueError("duration_seconds debe ser numérico") from exc
    if duration <= 0:
        raise ValueError("duration_seconds debe ser mayor que cero")
    try:
        datetime.fromisoformat(str(raw["recorded_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("recorded_at debe ser ISO-8601") from exc

    consent = raw["consent"]
    if not isinstance(consent, dict):
        raise ValueError("consent debe ser un objeto estructurado")
    boolean_flags = ("process_for_notes", "retain_audio", "asr_training", "tts_voice_training")
    if any(type(consent.get(flag)) is not bool for flag in boolean_flags):
        raise ValueError("los permisos deben ser booleanos explícitos")
    if not consent["process_for_notes"]:
        raise ValueError("process_for_notes es obligatorio para grabar")
    if not consent["retain_audio"]:
        raise ValueError("retain_audio es obligatorio mientras el prototipo guarda el audio")
    if consent.get("confirmation_method") not in {"oral_recorded", "signature", "other"}:
        raise ValueError("confirmation_method no es válido")
    if not str(consent.get("form_version", "")).strip():
        raise ValueError("form_version es obligatorio")

    return {
        "speaker_id": speaker_id,
        "dialect": raw["dialect"],
        "municipality": municipality,
        "duration_seconds": duration,
        "recorded_at": raw["recorded_at"],
        "consent": {key: consent[key] for key in (*boolean_flags, "confirmation_method", "form_version")},
    }


def save_recording(metadata: dict, audio: bytes, mime_type: str) -> dict:
    if not audio:
        raise ValueError("El audio está vacío")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    recording_id = f"rec_{uuid.uuid4().hex}"
    extension = ".webm" if "webm" in mime_type else ".ogg"
    relative_audio_path = f"recordings/{recording_id}{extension}"
    (DATA_DIR / relative_audio_path).write_bytes(audio)
    record = {
        "recording_id": recording_id,
        **validate_metadata(metadata),
        "audio_path": relative_audio_path,
        "audio_mime_type": mime_type,
        "consent_status": "active",
        "consent_captured_at": datetime.now(timezone.utc).isoformat(),
    }
    with MANIFEST.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_POST(self) -> None:
        if self.path != "/api/recordings":
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
            )
            metadata = json.loads(form.getvalue("metadata"))
            audio_field = form["audio"]
            record = save_recording(metadata, audio_field.file.read(), audio_field.type or "audio/webm")
            self.respond(HTTPStatus.CREATED, record)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.respond(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def respond(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8000"))
    print(f"Granola disponible en http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()

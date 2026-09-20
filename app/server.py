#!/usr/bin/env python3
"""Minimal server for consent-aware audio capture and corpus exports."""
from __future__ import annotations

import argparse
import cgi
import html
import json
import os
import re
import threading
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
_MANIFEST_LOCK = threading.Lock()
DIALECTS = {"central", "santa_maria_de_jesus", "santo_domingo_xenacoj", "south_central", "western", "yepocapa"}
PURPOSE_FLAGS = {"asr": "asr_training", "tts": "tts_voice_training"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_speaker_id(value: object) -> str:
    speaker_id = str(value).strip()
    if not re.fullmatch(r"[A-Za-z0-9_-]{2,64}", speaker_id):
        raise ValueError("speaker_id debe ser un seudónimo de 2-64 caracteres (letras, números, _ o -)")
    return speaker_id


def validate_metadata(raw: dict) -> dict:
    """Validate and normalize metadata accompanying one recording."""
    required = ("speaker_id", "dialect", "municipality", "duration_seconds", "recorded_at", "consent")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"Faltan campos: {', '.join(missing)}")
    speaker_id = validate_speaker_id(raw["speaker_id"])
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
    return {"speaker_id": speaker_id, "dialect": raw["dialect"], "municipality": municipality,
            "duration_seconds": duration, "recorded_at": raw["recorded_at"],
            "consent": {key: consent[key] for key in (*boolean_flags, "confirmation_method", "form_version")}}


def append_manifest(event: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with _MANIFEST_LOCK, MANIFEST.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def read_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    events = []
    with _MANIFEST_LOCK, MANIFEST.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Manifiesto inválido en línea {number}") from exc
    return events


def save_recording(metadata: dict, audio: bytes, mime_type: str) -> dict:
    if not audio:
        raise ValueError("El audio está vacío")
    if os.environ.get("GRANOLA_GCS_BUCKET"):
        raise ValueError("El backend GCS directo aún es un stub; monte el bucket en GRANOLA_DATA_DIR")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    recording_id = f"rec_{uuid.uuid4().hex}"
    extension = ".webm" if "webm" in mime_type else ".ogg"
    relative_audio_path = f"recordings/{recording_id}{extension}"
    (DATA_DIR / relative_audio_path).write_bytes(audio)
    record = {"event_type": "recording", "recording_id": recording_id, **validate_metadata(metadata),
              "audio_path": relative_audio_path, "audio_mime_type": mime_type,
              "consent_status": "active", "consent_captured_at": utc_now()}
    append_manifest(record)
    return record


def change_consent(raw: dict) -> dict:
    speaker_id = validate_speaker_id(raw.get("speaker_id", ""))
    flags = {}
    for flag in ("asr_training", "tts_voice_training"):
        if flag in raw:
            if type(raw[flag]) is not bool:
                raise ValueError(f"{flag} debe ser booleano")
            flags[flag] = raw[flag]
    if not flags:
        raise ValueError("Indique asr_training o tts_voice_training")
    status = "withdrawn" if flags.get("asr_training") is False and flags.get("tts_voice_training") is False else "restricted"
    event = {"event_type": "consent_change", "speaker_id": speaker_id, **flags,
             "consent_status": status, "changed_at": utc_now()}
    append_manifest(event)
    return event


def effective_consents(events: list[dict]) -> dict[str, dict]:
    state: dict[str, dict] = {}
    for event in events:
        speaker_id = event.get("speaker_id")
        if event.get("event_type", "recording") == "recording" and speaker_id not in state:
            consent = event.get("consent", {})
            state[speaker_id] = {flag: bool(consent.get(flag)) for flag in PURPOSE_FLAGS.values()}
        elif event.get("event_type") == "consent_change":
            current = state.setdefault(speaker_id, {"asr_training": False, "tts_voice_training": False})
            for flag in PURPOSE_FLAGS.values():
                if flag in event:
                    current[flag] = event[flag]
            current["changed_at"] = event.get("changed_at")
    return state


def export_records(purpose: str, output: Path) -> list[dict]:
    if purpose not in PURPOSE_FLAGS:
        raise ValueError("purpose debe ser asr o tts")
    events = read_manifest()
    consents = effective_consents(events)
    flag = PURPOSE_FLAGS[purpose]
    records = [event for event in events if event.get("event_type", "recording") == "recording"
               and event.get("consent_status") == "active"
               and event.get("consent", {}).get(flag) is True
               and consents.get(event.get("speaker_id"), {}).get(flag) is True]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
    return records


def admin_html() -> bytes:
    events = read_manifest()
    consents = effective_consents(events)
    recordings = {}
    for event in events:
        if event.get("event_type", "recording") == "recording":
            recordings[event["speaker_id"]] = recordings.get(event["speaker_id"], 0) + 1
    rows = "".join(f"<tr><td>{html.escape(speaker)}</td><td>{recordings.get(speaker, 0)}</td>"
                   f"<td>{'sí' if state.get('asr_training') else 'no'}</td>"
                   f"<td>{'sí' if state.get('tts_voice_training') else 'no'}</td>"
                   f"<td>{html.escape(state.get('changed_at', ''))}</td></tr>"
                   for speaker, state in sorted(consents.items()))
    return ("<!doctype html><html lang='es'><meta charset='utf-8'><title>Manifiesto Granola</title>"
            "<style>body{font-family:system-ui;max-width:900px;margin:2rem auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccc;padding:.5rem;text-align:left}</style>"
            "<h1>Estado de consentimiento</h1><table><thead><tr><th>Seudónimo</th><th>Grabaciones</th><th>ASR</th><th>TTS</th><th>Último cambio</th></tr></thead>"
            f"<tbody>{rows}</tbody></table></html>").encode()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB), **kwargs)

    def do_GET(self) -> None:
        if self.path == "/admin":
            body = admin_html()
            self.send_response(HTTPStatus.OK); self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return
        super().do_GET()

    def do_POST(self) -> None:
        try:
            if self.path == "/api/recordings":
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers,
                    environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")})
                metadata = json.loads(form.getvalue("metadata")); audio_field = form["audio"]
                self.respond(HTTPStatus.CREATED, save_recording(metadata, audio_field.file.read(), audio_field.type or "audio/webm")); return
            if self.path == "/api/consent":
                length = int(self.headers.get("Content-Length", "0"))
                self.respond(HTTPStatus.CREATED, change_consent(json.loads(self.rfile.read(length)))); return
            self.send_error(HTTPStatus.NOT_FOUND)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            self.respond(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def respond(self, status: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


def main() -> None:
    parser = argparse.ArgumentParser(description="Servidor y exportador de Granola")
    sub = parser.add_subparsers(dest="command")
    export = sub.add_parser("export", help="Exporta registros elegibles")
    export.add_argument("--purpose", choices=sorted(PURPOSE_FLAGS), required=True)
    export.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "export":
        records = export_records(args.purpose, args.output)
        print(f"Exportados {len(records)} registros a {args.output}")
        return
    port = int(os.environ.get("PORT", "8000"))
    print(f"Granola disponible en http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()

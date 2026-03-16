from __future__ import annotations

import json
import os
import socket
import sys
import webbrowser
from pathlib import Path
from threading import Timer

from flask import Flask, abort, jsonify, render_template, request, send_from_directory
from waitress import serve

from detector_service import DetectionService


APP_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 512 * 1024 * 1024

    service = DetectionService(APP_DIR)

    @app.errorhandler(Exception)
    def handle_exception(error):
        status_code = getattr(error, "code", 500)
        message = str(error) if str(error) else "Unexpected server error"
        return jsonify({"ok": False, "error": message}), status_code

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/models")
    def models():
        available_models = service.get_available_models()
        return jsonify(
            {
                "ok": True,
                "models": available_models,
                "default_model": available_models[0],
            }
        )

    @app.post("/api/detect/frame")
    def detect_frame():
        payload = request.get_json(force=True)
        image_data = payload.get("image_data")
        if not image_data:
            return jsonify({"ok": False, "error": "Missing image_data"}), 400

        settings = payload.get("settings", {})
        session_id = payload.get("session_id")
        result = service.detect_webcam_frame(image_data, settings, session_id)
        return jsonify({"ok": True, **result})

    @app.post("/api/detect/image")
    def detect_image():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"ok": False, "error": "Image file is required"}), 400

        settings = _parse_settings(request.form.get("settings"))
        log_csv = _as_bool(request.form.get("log_csv"))
        result = service.detect_image(upload.read(), settings, log_csv=log_csv)
        return jsonify({"ok": True, **result})

    @app.post("/api/process/video")
    def process_video():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"ok": False, "error": "Video file is required"}), 400

        settings = _parse_settings(request.form.get("settings"))
        log_csv = _as_bool(request.form.get("log_csv"))
        result = service.process_video(upload, settings, log_csv=log_csv)
        return jsonify({"ok": True, **result})

    @app.post("/api/save-snapshot")
    def save_snapshot():
        upload = request.files.get("file")
        if upload is not None and upload.filename:
            result = service.save_snapshot_file(upload.read())
            return jsonify({"ok": True, **result})

        payload = request.get_json(silent=True) or {}
        image_data = payload.get("image_data")
        if not image_data:
            return jsonify({"ok": False, "error": "Snapshot data is required"}), 400

        result = service.save_snapshot_data_url(image_data)
        return jsonify({"ok": True, **result})

    @app.post("/api/save-recording")
    def save_recording():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"ok": False, "error": "Recording file is required"}), 400

        result = service.save_recording(upload)
        return jsonify({"ok": True, **result})

    @app.post("/api/session/end")
    def end_session():
        payload = request.get_json(force=True)
        session_id = payload.get("session_id")
        if not session_id:
            return jsonify({"ok": False, "error": "session_id is required"}), 400

        result = service.finish_live_csv_session(session_id)
        return jsonify({"ok": True, **result})

    @app.get("/media/<category>/<path:filename>")
    def media(category: str, filename: str):
        directories = {
            "captures": service.capture_dir,
            "csv": service.csv_dir,
        }
        directory = directories.get(category)
        if directory is None:
            abort(404)
        return send_from_directory(directory, filename, as_attachment=False)

    return app


def _parse_settings(raw_settings: str | None) -> dict:
    if not raw_settings:
        return {}
    try:
        return json.loads(raw_settings)
    except json.JSONDecodeError:
        return {}


def _as_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


app = create_app()


def _should_open_browser() -> bool:
    if os.environ.get("NO_BROWSER") == "1":
        return False
    if sys.platform in {"win32", "darwin"}:
        return True
    return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


def _find_available_port(host: str, start_port: int, attempts: int = 20) -> int:
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
            except OSError:
                continue
            return port
    raise OSError("No free local port available for the web app.")


if __name__ == "__main__":
    port = _find_available_port(HOST, DEFAULT_PORT)
    app_url = f"http://{HOST}:{port}"
    if _should_open_browser():
        Timer(1.0, lambda: webbrowser.open(app_url)).start()
    print(f"[serve] {app_url}")
    serve(app, host=HOST, port=port, threads=6)

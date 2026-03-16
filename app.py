from __future__ import annotations

import json
import os
import socket
import sys
import webbrowser
from pathlib import Path
from threading import Timer
from urllib.parse import quote

from flask import Flask, jsonify, make_response, render_template, request
from waitress import serve

from services import LiveDetectionService


APP_DIR = Path(__file__).resolve().parent
HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["MAX_CONTENT_LENGTH"] = 64 * 1024 * 1024

    service = LiveDetectionService(APP_DIR)

    @app.errorhandler(Exception)
    def handle_exception(error):
        status_code = getattr(error, "code", 500)
        message = str(error) if str(error) else "Unexpected server error"
        return jsonify({"ok": False, "error": message}), status_code

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.post("/api/detect/frame")
    def detect_frame():
        upload = request.files.get("file")
        if upload is None or not upload.filename:
            return jsonify({"ok": False, "error": "Webcam frame file is required"}), 400

        settings = _parse_settings(request.form.get("settings"))
        result = service.detect_frame_bytes(upload.read(), settings)
        if request.headers.get("X-Response-Mode") == "jpeg":
            response = make_response(result["image_bytes"])
            response.headers["Content-Type"] = "image/jpeg"
            response.headers["Cache-Control"] = "no-store"
            response.headers["X-Live-Summary"] = quote(
                json.dumps(result["summary"], separators=(",", ":"), ensure_ascii=True),
                safe="",
            )
            response.headers["X-Frame-Perf"] = quote(
                json.dumps(result["perf"], separators=(",", ":"), ensure_ascii=True),
                safe="",
            )
            return response

        payload = dict(result)
        payload.pop("image_bytes", None)
        return jsonify({"ok": True, **payload})

    return app


def _parse_settings(raw_settings: str | None) -> dict:
    if not raw_settings:
        return {}
    try:
        return json.loads(raw_settings)
    except json.JSONDecodeError:
        return {}


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

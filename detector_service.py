from __future__ import annotations

import base64
import csv
import threading
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class DetectionService:
    def __init__(self, base_dir: Path):
        self.base_dir = Path(base_dir)
        self.model_dir = self.base_dir / "model"
        self.capture_dir = self.base_dir / "captures"
        self.csv_dir = self.base_dir / "csv_logs"
        self.upload_dir = self.base_dir / "uploads"

        for directory in (self.model_dir, self.capture_dir, self.csv_dir, self.upload_dir):
            directory.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.current_model_source = ""
        self.model_lock = threading.Lock()
        self.inference_lock = threading.Lock()
        self.device = self._detect_device()
        self.use_half = self.device.startswith("cuda")

        self.live_csv_sessions: dict[str, dict] = {}
        self.live_csv_lock = threading.RLock()

    def get_available_models(self) -> list[str]:
        model_paths = []
        for pattern in ("*.pt", "*.engine"):
            model_paths.extend(self.model_dir.glob(pattern))

        models = sorted({path.name for path in model_paths})
        if not models:
            return ["yolo26n.pt"]
        return models

    def detect_webcam_frame_data_url(self, image_data: str, settings: dict, session_id: str | None) -> dict:
        frame = self._decode_data_url_to_bgr(image_data)
        return self._detect_webcam_frame_bgr(frame, settings, session_id)

    def detect_webcam_frame_bytes(self, file_bytes: bytes, settings: dict, session_id: str | None) -> dict:
        frame = self._decode_bytes_to_bgr(file_bytes)
        return self._detect_webcam_frame_bgr(frame, settings, session_id)

    def _detect_webcam_frame_bgr(self, frame: np.ndarray, settings: dict, session_id: str | None) -> dict:
        result = self._run_detection(frame, settings)

        csv_url = None
        if self._as_bool(settings.get("log_csv")):
            session_id = session_id or self._start_live_csv_session()
            session_id, csv_url = self._append_live_csv_row(session_id, result["summary"])

        return {
            "image_data": self._bgr_to_data_url(result["annotated_frame"], quality=76),
            "summary": result["summary"],
            "session_id": session_id,
            "csv_url": csv_url,
        }

    def detect_image(self, file_bytes: bytes, settings: dict, log_csv: bool = False) -> dict:
        frame = self._decode_bytes_to_bgr(file_bytes)
        result = self._run_detection(frame, settings)

        csv_url = None
        if log_csv:
            csv_url = self._write_single_csv("image", result["summary"])

        return {
            "image_data": self._bgr_to_data_url(result["annotated_frame"], quality=86),
            "summary": result["summary"],
            "csv_url": csv_url,
        }

    def process_video(self, upload: FileStorage, settings: dict, log_csv: bool = False) -> dict:
        input_path = self._store_upload(upload)
        cap = cv2.VideoCapture(str(input_path))
        if not cap.isOpened():
            input_path.unlink(missing_ok=True)
            raise ValueError("Failed to open uploaded video file.")

        fps = cap.get(cv2.CAP_PROP_FPS) or 20.0
        if fps <= 0:
            fps = 20.0

        first_ok, first_frame = cap.read()
        if not first_ok:
            cap.release()
            input_path.unlink(missing_ok=True)
            raise ValueError("Uploaded video has no readable frames.")

        height, width = first_frame.shape[:2]
        writer, output_path = self._create_video_writer("processed_video", width, height, fps)

        csv_file = None
        csv_writer = None
        csv_url = None
        if log_csv:
            csv_path = self.csv_dir / f"video_log_{self._timestamp()}.csv"
            csv_file = csv_path.open("w", newline="", encoding="utf-8")
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["Frame", "Seconds", "Total Objects", "Details"])
            csv_url = self._csv_url(csv_path)

        aggregate_counts: Counter[str] = Counter()
        frames_processed = 0
        detections_total = 0
        peak_objects = 0

        try:
            frame = first_frame
            while True:
                result = self._run_detection(frame, settings)
                frame_counts = Counter({item["name"]: item["count"] for item in result["summary"]["by_class"]})
                frame_total = result["summary"]["total_objects"]

                frames_processed += 1
                detections_total += frame_total
                peak_objects = max(peak_objects, frame_total)
                aggregate_counts.update(frame_counts)

                writer.write(result["annotated_frame"])

                if csv_writer is not None:
                    csv_writer.writerow(
                        [
                            frames_processed,
                            f"{frames_processed / fps:.3f}",
                            frame_total,
                            result["summary"]["detail_text"],
                        ]
                    )

                ok, frame = cap.read()
                if not ok:
                    break
        finally:
            cap.release()
            writer.release()
            input_path.unlink(missing_ok=True)
            if csv_file is not None:
                csv_file.close()

        summary = {
            "frames_processed": frames_processed,
            "detections_total": detections_total,
            "peak_objects_in_frame": peak_objects,
            "by_class": self._counter_to_sorted_list(aggregate_counts),
        }

        return {
            "processed_video_url": self._capture_url(output_path),
            "csv_url": csv_url,
            "summary": summary,
        }

    def save_snapshot_file(self, file_bytes: bytes) -> dict:
        frame = self._decode_bytes_to_bgr(file_bytes)
        return self._save_snapshot_bgr(frame)

    def save_snapshot_data_url(self, image_data: str) -> dict:
        frame = self._decode_data_url_to_bgr(image_data)
        return self._save_snapshot_bgr(frame)

    def save_recording(self, upload: FileStorage) -> dict:
        extension = Path(secure_filename(upload.filename or "recording.webm")).suffix or ".webm"
        filename = self.capture_dir / f"record_{self._timestamp()}{extension}"
        upload.save(filename)
        return {
            "file_url": self._capture_url(filename),
            "filename": filename.name,
        }

    def finish_live_csv_session(self, session_id: str) -> dict:
        with self.live_csv_lock:
            session = self.live_csv_sessions.pop(session_id, None)

        if session is None:
            return {"csv_url": None}

        session["file"].close()
        return {"csv_url": self._csv_url(session["path"])}

    def _run_detection(self, frame: np.ndarray, settings: dict) -> dict:
        model_name = str(settings.get("model_name") or self.get_available_models()[0])
        model = self._load_model(model_name)
        inference_kwargs = self._build_inference_kwargs(settings)

        with self.inference_lock, torch.inference_mode():
            results = model(frame, **inference_kwargs)

        annotated_frame = results[0].plot()
        summary = self._summarize_results(results, model)
        return {
            "annotated_frame": annotated_frame,
            "summary": summary,
        }

    def _load_model(self, model_name: str):
        model_path = self.model_dir / model_name
        model_source = str(model_path) if model_path.is_file() else model_name

        with self.model_lock:
            if self.model is None or self.current_model_source != model_source:
                self.model = YOLO(model_source)
                self.current_model_source = model_source
            return self.model

    def _build_inference_kwargs(self, settings: dict) -> dict:
        confidence = self._clamp_float(settings.get("conf"), 0.25, minimum=0.01, maximum=1.0)
        iou = self._clamp_float(settings.get("iou"), 0.45, minimum=0.01, maximum=1.0)
        resolution = str(settings.get("resolution") or "640")
        class_filter = self._parse_class_filter(settings.get("class_filter", ""))

        kwargs = {
            "conf": confidence,
            "iou": iou,
            "device": self.device,
            "verbose": False,
        }

        if class_filter:
            kwargs["classes"] = class_filter

        if self.use_half:
            kwargs["half"] = True

        if resolution != "Native":
            try:
                kwargs["imgsz"] = int(resolution)
            except ValueError:
                pass

        return kwargs

    def _summarize_results(self, results, model) -> dict:
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return {
                "total_objects": 0,
                "by_class": [],
                "detail_text": "No objects detected.",
            }

        names = model.names
        class_ids = boxes.cls.cpu().numpy().astype(int).tolist()
        counts = Counter(names[class_id] for class_id in class_ids)

        return {
            "total_objects": sum(counts.values()),
            "by_class": self._counter_to_sorted_list(counts),
            "detail_text": ", ".join(f"{name}:{count}" for name, count in counts.items()),
        }

    def _counter_to_sorted_list(self, counter: Counter[str]) -> list[dict]:
        return [
            {"name": name, "count": count}
            for name, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
        ]

    def _start_live_csv_session(self) -> str:
        session_id = uuid.uuid4().hex
        csv_path = self.csv_dir / f"live_log_{self._timestamp()}_{session_id[:8]}.csv"
        csv_file = csv_path.open("w", newline="", encoding="utf-8")
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(["Timestamp", "Total Objects", "Details"])

        with self.live_csv_lock:
            self.live_csv_sessions[session_id] = {
                "file": csv_file,
                "writer": csv_writer,
                "path": csv_path,
            }

        return session_id

    def _append_live_csv_row(self, session_id: str, summary: dict) -> tuple[str, str]:
        with self.live_csv_lock:
            session = self.live_csv_sessions.get(session_id)
            if session is None:
                session_id = self._start_live_csv_session()
                session = self.live_csv_sessions[session_id]

            session["writer"].writerow(
                [
                    datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    summary["total_objects"],
                    summary["detail_text"],
                ]
            )
            session["file"].flush()
            return session_id, self._csv_url(session["path"])

    def _write_single_csv(self, prefix: str, summary: dict) -> str:
        csv_path = self.csv_dir / f"{prefix}_log_{self._timestamp()}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(["Timestamp", "Total Objects", "Details"])
            csv_writer.writerow(
                [
                    datetime.now().strftime("%H:%M:%S.%f")[:-3],
                    summary["total_objects"],
                    summary["detail_text"],
                ]
            )
        return self._csv_url(csv_path)

    def _save_snapshot_bgr(self, frame: np.ndarray) -> dict:
        filename = self.capture_dir / f"snapshot_{self._timestamp()}.jpg"
        cv2.imwrite(str(filename), frame)
        return {
            "file_url": self._capture_url(filename),
            "filename": filename.name,
        }

    def _store_upload(self, upload: FileStorage) -> Path:
        original_name = secure_filename(upload.filename or "upload.bin")
        extension = Path(original_name).suffix or ".bin"
        stored_path = self.upload_dir / f"upload_{self._timestamp()}_{uuid.uuid4().hex[:8]}{extension}"
        upload.save(stored_path)
        return stored_path

    def _create_video_writer(self, stem: str, width: int, height: int, fps: float):
        for extension, fourcc_name in ((".mp4", "mp4v"), (".avi", "MJPG")):
            filename = self.capture_dir / f"{stem}_{self._timestamp()}{extension}"
            writer = cv2.VideoWriter(
                str(filename),
                cv2.VideoWriter_fourcc(*fourcc_name),
                fps,
                (width, height),
            )
            if writer.isOpened():
                return writer, filename
            writer.release()
        raise RuntimeError("Could not create output video writer.")

    def _decode_bytes_to_bgr(self, file_bytes: bytes) -> np.ndarray:
        array = np.frombuffer(file_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Failed to decode image bytes.")
        return frame

    def _decode_data_url_to_bgr(self, image_data: str) -> np.ndarray:
        try:
            encoded = image_data.split(",", 1)[1]
        except IndexError as exc:
            raise ValueError("Invalid image data URL.") from exc

        file_bytes = base64.b64decode(encoded)
        return self._decode_bytes_to_bgr(file_bytes)

    def _bgr_to_data_url(self, frame: np.ndarray, quality: int = 88) -> str:
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not success:
            raise ValueError("Failed to encode output frame.")
        encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    def _capture_url(self, path: Path) -> str:
        return f"/media/captures/{path.name}"

    def _csv_url(self, path: Path) -> str:
        return f"/media/csv/{path.name}"

    def _parse_class_filter(self, raw_value) -> list[int] | None:
        if raw_value is None:
            return None

        if isinstance(raw_value, list):
            values = raw_value
        else:
            values = str(raw_value).split(",")

        parsed = []
        for value in values:
            value_str = str(value).strip()
            if value_str.isdigit():
                parsed.append(int(value_str))

        return parsed or None

    def _clamp_float(self, value, default: float, minimum: float, maximum: float) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return default
        return max(minimum, min(maximum, numeric))

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def _as_bool(self, value) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _detect_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

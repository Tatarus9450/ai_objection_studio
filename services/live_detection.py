from __future__ import annotations

import base64
import time
from pathlib import Path

import cv2
import numpy as np

from .model_runtime import ModelRuntime


class LiveDetectionService:
    def __init__(self, base_dir: Path):
        base_dir = Path(base_dir)
        self.model_runtime = ModelRuntime(base_dir / "model")

    def detect_frame_bytes(self, file_bytes: bytes, settings: dict) -> dict:
        started_at = time.perf_counter()
        frame = self._decode_bytes_to_bgr(file_bytes)
        decoded_at = time.perf_counter()
        result = self.model_runtime.run_frame(frame, settings)
        detected_at = time.perf_counter()
        image_bytes = self._bgr_to_jpeg_bytes(result["annotated_frame"], quality=70)
        encoded_at = time.perf_counter()
        return {
            "image_bytes": image_bytes,
            "image_data": self._jpeg_bytes_to_data_url(image_bytes),
            "summary": result["summary"],
            "perf": {
                "decode_ms": round((decoded_at - started_at) * 1000, 1),
                "detect_ms": round((detected_at - decoded_at) * 1000, 1),
                "encode_ms": round((encoded_at - detected_at) * 1000, 1),
                "total_ms": round((encoded_at - started_at) * 1000, 1),
            },
        }

    def _decode_bytes_to_bgr(self, file_bytes: bytes) -> np.ndarray:
        array = np.frombuffer(file_bytes, dtype=np.uint8)
        frame = cv2.imdecode(array, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Failed to decode webcam frame.")
        return frame

    def _bgr_to_jpeg_bytes(self, frame: np.ndarray, quality: int) -> bytes:
        success, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if not success:
            raise ValueError("Failed to encode output frame.")
        return buffer.tobytes()

    def _jpeg_bytes_to_data_url(self, image_bytes: bytes) -> str:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

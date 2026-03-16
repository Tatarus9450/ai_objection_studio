from __future__ import annotations

import threading
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from ultralytics import YOLO


DEFAULT_MODEL_NAME = "kanom_v2.pt"


class ModelRuntime:
    def __init__(self, model_dir: Path):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        self.model = None
        self.current_model_source = ""
        self.model_lock = threading.Lock()
        self.inference_lock = threading.Lock()
        self.device = self._detect_device()
        self.use_half = self.device.startswith("cuda")

    def run_frame(self, frame: np.ndarray, settings: dict) -> dict:
        model = self._load_model()
        inference_kwargs = self._build_inference_kwargs(settings)

        with self.inference_lock, torch.inference_mode():
            results = model(frame, **inference_kwargs)

        return {
            "annotated_frame": results[0].plot(),
            "summary": self._summarize_results(results, model),
        }

    def _load_model(self):
        model_path = self.model_dir / DEFAULT_MODEL_NAME
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Model not found: {DEFAULT_MODEL_NAME}. "
                f"Expected file at {model_path}."
            )
        model_source = str(model_path)

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
                "detail_text": "ไม่พบขนมในเฟรมนี้",
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

    def _parse_class_filter(self, raw_value) -> list[int] | None:
        if raw_value is None:
            return None

        values = raw_value if isinstance(raw_value, list) else str(raw_value).split(",")
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

    def _detect_device(self) -> str:
        if torch.cuda.is_available():
            return "cuda:0"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

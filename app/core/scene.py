import base64
import hashlib
import io
import queue
import threading

import torch
from diffusers import LCMScheduler, StableDiffusionPipeline
from PySide6.QtCore import QThread, Signal

from core import scene_api


class SceneWorker(QThread):
    scene_ready = Signal(str, str)
    scene_failed = Signal(str, str)
    status_changed = Signal(str)
    model_loaded = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        self._pipe = None
        self._device = "cpu"

    def generate(self, sentence: str):
        if not sentence:
            return
        self._queue.put(sentence.strip())

    def stop(self):
        self._stop_event.set()
        try:
            self._queue.put_nowait("")
        except Exception:
            pass

    def _load_model(self):
        model_path = "/home/medo/models/LCM_Dreamshaper_v7_4k.safetensors"
        self.status_changed.emit("Loading scene model...")
        try:
            if torch.cuda.is_available():
                self._device = "cuda"
                torch_dtype = torch.float16
            else:
                self._device = "cpu"
                torch_dtype = torch.float32

            self._pipe = StableDiffusionPipeline.from_single_file(
                model_path,
                torch_dtype=torch_dtype,
                safety_checker=None,
                requires_safety_checker=False,
            )
            self._pipe.scheduler = LCMScheduler.from_config(self._pipe.scheduler.config)
            self._pipe = self._pipe.to(self._device)

            self.model_loaded.emit(True, self._device)
            self.status_changed.emit(f"Scene model ready ({self._device})")
            return True
        except Exception as e:
            self.status_changed.emit(f"Model load failed: {e}")
            self.model_loaded.emit(False, self._device)
            return False

    def run(self):
        if not self._load_model():
            while not self._stop_event.is_set():
                try:
                    item = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if item == "" or self._stop_event.is_set():
                    break
                self.scene_failed.emit(item, "Model not loaded")
            return

        while not self._stop_event.is_set():
            try:
                sentence = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if sentence == "" or self._stop_event.is_set():
                break

            try:
                processed = scene_api.process_sentence(sentence)
                if not processed or not processed.get("prompt"):
                    self.scene_failed.emit(
                        sentence, "Failed to get prompt from backend"
                    )
                    self.status_changed.emit("Scene generation failed")
                    continue

                defaults = processed.get("defaults") or {}
                seed = int(hashlib.sha256(sentence.encode("utf-8")).hexdigest(), 16) % (
                    2**31
                )
                generator = torch.Generator(device=self._device).manual_seed(seed)

                self.status_changed.emit("Generating scene...")
                image = self._pipe(
                    prompt=processed["prompt"],
                    negative_prompt=processed.get("negative_prompt", ""),
                    num_inference_steps=int(defaults.get("num_inference_steps", 4)),
                    guidance_scale=float(defaults.get("guidance_scale", 1.0)),
                    width=int(defaults.get("width", 512)),
                    height=int(defaults.get("height", 512)),
                    generator=generator,
                ).images[0]

                buf = io.BytesIO()
                image.save(buf, format="JPEG", quality=82)
                b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                self.scene_ready.emit(sentence, f"data:image/jpeg;base64,{b64}")
                self.status_changed.emit("Scene ready")
            except Exception as e:
                self.scene_failed.emit(sentence, str(e))
                self.status_changed.emit("Scene generation failed")

"""
auth/enroll_manager.py — Guided face enrollment: capture N good frames → average embedding → store.
Called from EnrollDialog (GUI) or admin screen.
"""
from __future__ import annotations
from typing import Callable
import cv2
import numpy as np
from loguru import logger
from auth.face_auth import face_analyzer
from auth.user_registry import registry


class EnrollManager:
    """
    Accumulates embeddings across multiple frames until TARGET_FRAMES good frames
    are collected, then stores the averaged embedding.
    """

    TARGET_FRAMES  = 20    # number of good frames to capture
    MIN_CONFIDENCE = 0.80  # minimum detection score to accept a frame
    MIN_BLUR       = 60.0  # lower is more blur; >60 is usually okay-ish, >100 is good

    def __init__(self):
        self._frames: list[np.ndarray] = []
        self._target_name: str = ""
        self._active: bool = False
        
        # Quality feedback
        self.last_rejection: str = ""
        self.best_frame_bgr: np.ndarray | None = None
        self.best_score: float = -1.0
        self.best_quality_data: dict = {}

    # ── Session control ───────────────────────────────────────────────────────

    def start(self, name: str) -> None:
        self._target_name = name.strip()
        self._frames = []
        self._active = True
        logger.info("Enrollment started for '{}'  (need {} frames)", name, self.TARGET_FRAMES)

    def cancel(self) -> None:
        self._active = False
        self._frames = []
        self.best_frame_bgr = None
        self.best_score = -1.0
        self.last_rejection = ""

    @property
    def is_active(self) -> bool:
        return self._active

    @property
    def progress(self) -> tuple[int, int]:
        """(captured, target)"""
        return len(self._frames), self.TARGET_FRAMES

    # ── Feed frames ───────────────────────────────────────────────────────────

    def feed_frame(self, bgr_frame: np.ndarray) -> bool:
        """
        Feed one camera frame.
        Returns True when enrollment is complete (TARGET_FRAMES reached).
        """
        if not self._active:
            return False

        face = face_analyzer.best_face(bgr_frame, self.MIN_CONFIDENCE)
        if face is None:
            self.last_rejection = "No face detected"
            return False

        # ── 1. Quality Check ──
        ok, reason, metrics = self._check_quality(bgr_frame, face)
        if not ok:
            self.last_rejection = reason
            return False

        emb = face_analyzer.get_embedding(bgr_frame, face)
        if emb is None:
            self.last_rejection = "Failed to extract features"
            return False

        self._frames.append(emb)
        self.last_rejection = "Capturing..."

        # Update best frame for preview
        total_score = metrics["sharpness"] + (metrics["size"] * 100)
        if total_score > self.best_score:
            self.best_score = total_score
            self.best_frame_bgr = bgr_frame.copy()
            self.best_quality_data = metrics

        if len(self._frames) >= self.TARGET_FRAMES:
            # We DON'T finalize yet — we wait for GUI to call save() after confirmation
            return True

        return False

    def _check_quality(self, frame: np.ndarray, face: dict) -> tuple[bool, str, dict]:
        """Verify face size, sharpness, and alignment."""
        # ── Sharpness ──
        gray = face_analyzer.crop_face(frame, face) # I need to check if crop_face exists or use alignCrop
        if gray is None:
             # fallback to simple bbox crop
             x, y, w, h = face["bbox"]
             gray = cv2.cvtColor(frame[y:y+h, x:x+w], cv2.COLOR_BGR2GRAY)
        else:
             gray = cv2.cvtColor(gray, cv2.COLOR_BGR2GRAY)
             
        laplacian = cv2.Laplacian(gray, cv2.CV_64F).var()
        
        # ── Size ──
        f_h, f_w = frame.shape[:2]
        w = face["bbox"][2]
        size_ratio = w / f_w
        
        # ── Alignment (horizontal eyes) ──
        lmks = face["landmarks"]
        left_eye, right_eye = lmks[0], lmks[1]
        dy = abs(left_eye[1] - right_eye[1])
        dx = abs(left_eye[0] - right_eye[0])
        tilt = dy / (dx + 1e-6)

        metrics = {"sharpness": laplacian, "size": size_ratio, "tilt": tilt}

        if laplacian < self.MIN_BLUR:
            return False, "Too blurry — stay still", metrics
        if size_ratio < 0.25:
            return False, "Too far — move closer", metrics
        if tilt > 0.2:
            return False, "Head tilted — look straight", metrics

        return True, "Good quality", metrics

    def finalize_and_save(self) -> int:
        """Call this after user confirms the capture in the GUI."""
        if not self._frames:
            return -1
        res = self._finalize()
        return res

    def _finalize(self) -> int:
        avg_embedding = np.mean(self._frames, axis=0).astype(np.float32)
        user_id = registry.enroll(self._target_name, avg_embedding, authorized=True)
        self._active = False
        self._frames = []
        return user_id


# Module-level singleton
enroll_manager = EnrollManager()

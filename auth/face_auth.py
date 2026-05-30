"""
auth/face_auth.py — Face detection + embedding using OpenCV DNN + ONNX models.

Models used (downloaded automatically on first init):
  Detection  : YuNet (opencv face detector, ~200KB)
  Recognition: SFace (opencv face recogniser, ~37MB)

Both are bundled with opencv-contrib-python or downloaded via urllib.
No C++ compiler required — pure Python + prebuilt wheels.
"""
from __future__ import annotations
import os
import urllib.request
from pathlib import Path
import numpy as np
import cv2
from loguru import logger


# ── Model URLs ────────────────────────────────────────────────────────────────
_MODEL_DIR = Path("models/face")
_DET_URL  = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
              "face_detection_yunet/face_detection_yunet_2023mar.onnx")
_REC_URL  = ("https://github.com/opencv/opencv_zoo/raw/main/models/"
              "face_recognition_sface/face_recognition_sface_2021dec.onnx")
_DET_FILE = _MODEL_DIR / "face_detection_yunet_2023mar.onnx"
_REC_FILE = _MODEL_DIR / "face_recognition_sface_2021dec.onnx"


def _download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        return True
    logger.info("Downloading {} → {}", url.split("/")[-1], dest)
    try:
        urllib.request.urlretrieve(url, dest)
        logger.info("Download complete: {}", dest.name)
        return True
    except Exception as exc:
        logger.error("Download failed: {}", exc)
        return False


class FaceAnalyzer:
    """
    YuNet (detection) + SFace (recognition) pipeline via OpenCV DNN.
    No C++ build tools required.
    """

    _instance: FaceAnalyzer | None = None

    def __new__(cls) -> FaceAnalyzer:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._detector  = None
            cls._instance._recognizer = None
            cls._instance._ready     = False
        return cls._instance

    def initialize(self, model: str = "yunet_sface") -> bool:
        """Download models if needed and load them. Returns True on success."""
        det_ok = _download(_DET_URL, _DET_FILE)
        rec_ok = _download(_REC_URL, _REC_FILE)
        if not (det_ok and rec_ok):
            logger.error("Model download failed — face auth unavailable")
            return False
        try:
            self._detector = cv2.FaceDetectorYN.create(
                str(_DET_FILE), "", (640, 480),
                score_threshold=0.75,
                nms_threshold=0.3,
                top_k=1,
            )
            self._recognizer = cv2.FaceRecognizerSF.create(str(_REC_FILE), "")
            self._ready = True
            logger.info("FaceAnalyzer ready (YuNet + SFace)")
            return True
        except Exception as exc:
            logger.error("FaceAnalyzer init error: {}", exc)
            return False

    @property
    def is_ready(self) -> bool:
        return self._ready

    def detect(self, bgr_frame: np.ndarray) -> list[dict]:
        """
        Returns list of face dicts:
          { 'bbox': [x,y,w,h], 'score': float, 'landmarks': np.ndarray(5x2) }
        """
        if not self._ready:
            return []
        h, w = bgr_frame.shape[:2]
        self._detector.setInputSize((w, h))
        ret_val, faces = self._detector.detect(bgr_frame)
        if faces is None or ret_val == 0:
            return []
        result = []
        for face in faces:
            score = float(face[14])
            bbox  = [int(face[0]), int(face[1]), int(face[2]), int(face[3])]
            lmks  = face[4:14].reshape(5, 2).astype(int)
            result.append({"bbox": bbox, "score": score, "landmarks": lmks, "_raw": face})
        return result

    def best_face(self, bgr_frame: np.ndarray, min_confidence: float = 0.75) -> dict | None:
        faces = self.detect(bgr_frame)
        if not faces:
            return None
        best = max(faces, key=lambda f: f["score"])
        return best if best["score"] >= min_confidence else None

    def crop_face(self, bgr_frame: np.ndarray, face: dict) -> np.ndarray | None:
        """Alignment-cropped face (112x112)."""
        if not self._ready or face is None:
            return None
        try:
            return self._recognizer.alignCrop(bgr_frame, face["_raw"])
        except Exception:
            return None

    def get_embedding(self, bgr_frame: np.ndarray, face: dict) -> np.ndarray | None:
        """Extract 128-d SFace embedding for a detected face."""
        if not self._ready or face is None:
            return None
        try:
            aligned = self._recognizer.alignCrop(bgr_frame, face["_raw"])
            feature = self._recognizer.feature(aligned)
            return feature.flatten()
        except Exception as exc:
            logger.debug("Embedding error: {}", exc)
            return None

    def embedding_from_frame(self, bgr_frame: np.ndarray, min_confidence: float = 0.75) -> np.ndarray | None:
        face = self.best_face(bgr_frame, min_confidence)
        if face is None:
            return None
        return self.get_embedding(bgr_frame, face)

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


# Module-level singleton
face_analyzer = FaceAnalyzer()

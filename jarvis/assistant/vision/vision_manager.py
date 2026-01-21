from __future__ import annotations

from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from mss import mss

from jarvis.utils.logger import get_logger


class VisionManager:
    """
    Provides screen capture and webcam frames for on-device vision tasks.
    """

    def __init__(self, temp_dir: Optional[Path] = None) -> None:
        self.logger = get_logger(__name__)
        self.temp_dir = temp_dir or Path.cwd() / "jarvis" / "data"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def capture_screen(self) -> Path:
        path = self.temp_dir / "screencap.png"
        with mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            img = np.array(sct_img)
            cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_BGRA2BGR))
        self.logger.info("Screen captured to %s", path)
        return path

    def capture_webcam(self, index: int = 0) -> Optional[Path]:
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            self.logger.error("Unable to access webcam at index %s", index)
            return None

        ret, frame = cap.read()
        cap.release()

        if not ret:
            self.logger.error("Failed to capture image from webcam.")
            return None

        path = self.temp_dir / "webcam.png"
        cv2.imwrite(str(path), frame)
        self.logger.info("Webcam snapshot saved to %s", path)
        return path

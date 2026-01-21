import cv2
import numpy as np

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.skills.base_skill import Skill, SkillMetadata
from jarvis.assistant.vision.vision_manager import VisionManager


class VisionSkill(Skill):
    metadata = SkillMetadata(
        name="Vision",
        description="Captures the screen or webcam and provides a lightweight description.",
        triggers=("grab screen", "screenshot", "webcam", "what do you see"),
    )

    def __init__(self) -> None:
        self.vision = VisionManager()

    async def handle(self, text: str, memory: MemoryManager) -> str:
        lowered = text.lower()
        if "screen" in lowered or "screenshot" in lowered:
            path = self.vision.capture_screen()
            description = self._describe_image(path)
            return f"I've captured the screen to {path}. {description}"

        if "webcam" in lowered or "what do you see" in lowered:
            path = self.vision.capture_webcam()
            if not path:
                return "I couldn't access the webcam."
            description = self._describe_image(path)
            return f"Webcam snapshot saved to {path}. {description}"

        return "I'm not sure which image you'd like me to capture."

    def _describe_image(self, path) -> str:
        image = cv2.imread(str(path))
        if image is None:
            return "However, I couldn't analyze the image content."

        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        brightness = np.mean(hsv[:, :, 2])
        contrast = np.std(hsv[:, :, 2])
        edges = cv2.Canny(image, 100, 200)
        edge_density = np.mean(edges > 0)

        brightness_desc = "dim" if brightness < 80 else "balanced" if brightness < 170 else "bright"
        contrast_desc = "soft" if contrast < 40 else "defined" if contrast < 80 else "high contrast"
        detail_desc = "minimal detail" if edge_density < 0.01 else "moderate detail" if edge_density < 0.03 else "high detail"

        return (
            f"The scene appears {brightness_desc} with {contrast_desc} lighting and {detail_desc}. "
            "I can provide a closer analysis if you need specifics."
        )

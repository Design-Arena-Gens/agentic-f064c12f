import threading
from typing import Optional, TYPE_CHECKING

from PIL import Image, ImageDraw
import pystray

from jarvis.utils.logger import get_logger

if TYPE_CHECKING:
    from jarvis.assistant.core import JarvisAssistant


class TrayApplication:
    """
    Provides a lightweight system tray icon to control Jarvis.
    """

    def __init__(self, assistant: "JarvisAssistant") -> None:
        self.logger = get_logger(__name__)
        self.assistant = assistant
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._icon is not None:
            return
        icon_image = self._create_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem("Wake Jarvis", lambda _icon, _item: self.assistant.listener.force_wake()),
            pystray.MenuItem("Sample Metrics", lambda _icon, _item: self.assistant.monitor.sample()),
            pystray.MenuItem("Exit", lambda _icon, _item: self.stop()),
        )
        self._icon = pystray.Icon("Jarvis", icon_image, "Jarvis Assistant", menu=menu)
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()
        self.logger.info("Tray icon started.")

    def stop(self) -> None:
        if self._icon:
            self._icon.stop()
            self._icon = None
        self.logger.info("Tray icon stopped.")

    @staticmethod
    def _create_icon_image() -> Image.Image:
        size = (64, 64)
        image = Image.new("RGB", size, "black")
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill="#1e90ff", outline="#87cefa", width=3)
        draw.ellipse((24, 24, 40, 40), fill="white")
        return image

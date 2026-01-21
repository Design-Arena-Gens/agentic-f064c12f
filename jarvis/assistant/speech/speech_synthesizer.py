import asyncio
from concurrent.futures import ThreadPoolExecutor

import pyttsx3

from jarvis.utils.logger import get_logger


class SpeechSynthesizer:
    """
    Generates spoken responses using the system's TTS capabilities.
    """

    def __init__(self) -> None:
        self.logger = get_logger(__name__)
        self.engine = pyttsx3.init()
        self.voice_lock = asyncio.Lock()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._configure_voice()

    def _configure_voice(self) -> None:
        voices = self.engine.getProperty("voices")
        for voice in voices:
            if "english" in voice.name.lower():
                self.engine.setProperty("voice", voice.id)
                break
        self.engine.setProperty("rate", 180)
        self.logger.debug("Configured pyttsx3 voice.")

    async def speak(self, text: str) -> None:
        async with self.voice_lock:
            self.logger.info("Speaking response: %s", text)
            await asyncio.get_running_loop().run_in_executor(self.executor, self._speak_blocking, text)

    def _speak_blocking(self, text: str) -> None:
        self.engine.say(text)
        self.engine.runAndWait()

    async def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.engine.stop()

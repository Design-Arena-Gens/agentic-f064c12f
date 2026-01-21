import asyncio
import re
from typing import Optional

import numpy as np
import sounddevice as sd
import whisper

from jarvis.assistant.memory.memory_manager import MemoryManager
from jarvis.assistant.speech.transcription import TranscriptionResult
from jarvis.utils.logger import get_logger

WAKE_WORD_PATTERN = re.compile(r"\bhey\s+jarvis\b", re.IGNORECASE)


class SpeechListener:
    """
    Captures live microphone audio, detects the wake word, and produces transcriptions.
    """

    def __init__(self, memory_manager: MemoryManager, sample_rate: int = 16000) -> None:
        self.logger = get_logger(__name__)
        self.memory = memory_manager
        self.sample_rate = sample_rate
        self.model = whisper.load_model("base")
        self.energy_threshold = 0.01
        self.silence_duration = 1.2
        self.max_phrase_seconds = 18
        self._wake_enabled = True
        self._forced_awake = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def configure_wake_word(self) -> None:
        # Placeholder for future wake word engines (e.g., openwakeword). For now, rely on transcription check.
        self.logger.info("Wake word detection configured: using transcription-based fallback.")

    async def listen(self) -> Optional[TranscriptionResult]:
        if not self._loop:
            self._loop = asyncio.get_running_loop()
        await self._wait_for_wake_word()
        self.logger.debug("Wake word detected. Listening for follow-up command.")

        audio = await asyncio.to_thread(self._record_phrase)
        if audio is None:
            return None

        text, confidence = await asyncio.to_thread(self._transcribe_audio, audio)
        if not text:
            return None

        intent = self._infer_intent(text)
        return TranscriptionResult(text=text, confidence=confidence, intent=intent)

    async def _wait_for_wake_word(self) -> None:
        if not self._wake_enabled:
            return
        self.logger.debug("Listening for wake word...")
        self._forced_awake.clear()
        while True:
            if self._forced_awake.is_set():
                self.logger.debug("Wake word bypassed from tray command.")
                self._forced_awake.clear()
                return
            audio = await asyncio.to_thread(self._record_phrase, phrase_time_limit=3.0)
            if audio is None:
                await asyncio.sleep(0.2)
                continue

            transcript, _ = await asyncio.to_thread(self._transcribe_audio, audio)
            if transcript and WAKE_WORD_PATTERN.search(transcript):
                return
            await asyncio.sleep(0.2)

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def force_wake(self) -> None:
        if self._loop:
            self._loop.call_soon_threadsafe(self._forced_awake.set)

    def _record_phrase(self, phrase_time_limit: Optional[float] = None) -> Optional[np.ndarray]:
        duration = phrase_time_limit or self.max_phrase_seconds
        self.logger.debug("Recording audio segment for %.1f seconds", duration)

        try:
            audio = sd.rec(int(duration * self.sample_rate), samplerate=self.sample_rate, channels=1, dtype="float32")
            sd.wait()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self.logger.exception("Audio capture failed: %s", exc)
            return None

        energy = float(np.linalg.norm(audio) / len(audio))
        self.logger.debug("Captured audio energy: %.5f", energy)

        if energy < self.energy_threshold:
            return None

        return audio.flatten()

    def _transcribe_audio(self, audio: np.ndarray) -> tuple[str, float]:
        result = self.model.transcribe(audio, fp16=False, language="en")

        text = result.get("text", "").strip()
        confidence = float(np.mean([seg.get("avg_logprob", -1.0) for seg in result.get("segments", [])]) + 1.0) / 2.0
        confidence = max(0.0, min(1.0, confidence))
        self.logger.debug("Transcription: '%s' (confidence %.2f)", text, confidence)
        return text, confidence

    @staticmethod
    def _infer_intent(text: str) -> str:
        lowered = text.lower()
        command_keywords = (
            "open ",
            "launch ",
            "start ",
            "close ",
            "shutdown",
            "restart",
            "monitor",
            "what's my cpu",
            "show me",
            "run ",
            "set ",
            "remember ",
        )
        if any(lowered.startswith(keyword) for keyword in command_keywords):
            return "command"
        return "conversation"

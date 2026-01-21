from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptionResult:
    text: str
    confidence: float
    intent: str = "conversation"
    command_keyword: Optional[str] = None

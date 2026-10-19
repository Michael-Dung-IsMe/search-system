"""Speech-to-text for Vietnamese voice queries via OpenAI."""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("transcriber")
OPENAI_STT_MODEL = "gpt-transcribe"


class SpeechTranscriber:
    """Converts spoken voice audio queries into Vietnamese text."""

    _instance: Optional[SpeechTranscriber] = None

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        use_mock: bool = False,
    ):
        self.openai_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        self.use_mock = use_mock

    def transcribe(
        self,
        audio_input: Union[bytes, Path, str],
        filename: str = "voice.webm",
        language: str = "vi",
    ) -> str:
        """Transcribes audio payload to clean text transcript."""
        if self.use_mock:
            return self._transcribe_mock(filename)

        # Refresh the key because local development may load .env after the
        # singleton was first created.
        api_key = self.openai_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            load_dotenv(override=True)
            api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for speech transcription")

        try:
            transcript = self._transcribe_openai(
                audio_input,
                filename,
                language,
                api_key=api_key,
            )
        except Exception as exc:
            logger.error("OpenAI %s transcription failed: %s", OPENAI_STT_MODEL, exc)
            raise RuntimeError("OpenAI speech transcription failed") from exc

        if not transcript:
            raise RuntimeError("OpenAI returned an empty speech transcript")

        logger.info("Transcribed audio using OpenAI %s: '%s'", OPENAI_STT_MODEL, transcript)
        return transcript

    def _transcribe_openai(
        self,
        audio_input: Union[bytes, Path, str],
        filename: str,
        language: str,
        api_key: Optional[str] = None,
    ) -> str:
        """Transcribes a completed audio file with OpenAI GPT Transcribe."""
        from openai import OpenAI

        client = OpenAI(api_key=api_key or self.openai_key)

        if isinstance(audio_input, bytes):
            file_obj = io.BytesIO(audio_input)
            file_obj.name = filename
            audio_payload = file_obj
        else:
            audio_payload = open(audio_input, "rb")

        try:
            transcript = client.audio.transcriptions.create(
                model=OPENAI_STT_MODEL,
                file=audio_payload,
                languages=[language],
            )
            return transcript.text.strip()
        finally:
            if hasattr(audio_payload, "close"):
                audio_payload.close()

    def _transcribe_mock(self, filename: str) -> str:
        """Generates deterministic fashion voice query mock for testing."""
        return "tìm đôi giày sneaker màu trắng không phải da dưới 1 triệu"

    @classmethod
    def get_instance(cls, use_mock: bool = False) -> SpeechTranscriber:
        """Singleton accessor for SpeechTranscriber."""
        if cls._instance is None or (use_mock and not getattr(cls._instance, "use_mock", False)):
            cls._instance = cls(use_mock=use_mock)
        return cls._instance

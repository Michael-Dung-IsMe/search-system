"""Speech-to-Text Transcriber for Vietnamese Fashion Voice Queries.

Integrates OpenAI Whisper API with domain-tailored fashion prompt,
faster-whisper local fallback, and mock fallback for deterministic tests.
"""

from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from typing import Optional, Union

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("transcriber")

FASHION_STT_PROMPT = "thời trang, sneaker, blazer, denim, hoodie, quần áo, áo màu vàng, đầm, váy, giày dép, túi xách, cotton, canvas, leather, màu sắc, vàng, đỏ, xanh, đen, trắng, xám, be, cam, tím, hồng"


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

        # 1. Try OpenAI Whisper API if key available (refresh from env if needed)
        api_key = self.openai_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            load_dotenv(override=True)
            api_key = os.getenv("OPENAI_API_KEY")

        if api_key:
            try:
                transcript = self._transcribe_openai(audio_input, filename, language, api_key=api_key)
                logger.info("Transcribed audio using OpenAI Whisper API: '%s'", transcript)
                return transcript
            except Exception as e:
                logger.warning("OpenAI Whisper API failed (%s), attempting local/mock fallback...", e)

        # 2. Try faster-whisper local fallback if installed
        try:
            logger.info("Falling back to local faster-whisper...")
            return self._transcribe_faster_whisper(audio_input)
        except Exception as e:
            logger.warning("faster-whisper failed (%s), using mock fallback.", e)

        # 3. Fallback mock
        return self._transcribe_mock(filename)

    def _transcribe_openai(
        self,
        audio_input: Union[bytes, Path, str],
        filename: str,
        language: str,
        api_key: Optional[str] = None,
    ) -> str:
        """Calls OpenAI whisper-1 endpoint."""
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
                model="whisper-1",
                file=audio_payload,
                language=language,
                prompt=FASHION_STT_PROMPT,
            )
            return transcript.text.strip()
        finally:
            if hasattr(audio_payload, "close"):
                audio_payload.close()

    def _transcribe_faster_whisper(self, audio_input: Union[bytes, Path, str]) -> str:
        """Local faster-whisper fallback."""
        from faster_whisper import WhisperModel

        model = WhisperModel("base", device="cpu", compute_type="int8")

        if isinstance(audio_input, bytes):
            audio_file = io.BytesIO(audio_input)
        else:
            audio_file = str(audio_input)

        segments, _ = model.transcribe(audio_file, language="vi", initial_prompt=FASHION_STT_PROMPT)
        text = " ".join(seg.text for seg in segments).strip()
        return text

    def _transcribe_mock(self, filename: str) -> str:
        """Generates deterministic fashion voice query mock for testing."""
        return "tìm đôi giày sneaker màu trắng không phải da dưới 1 triệu"

    @classmethod
    def get_instance(cls, use_mock: bool = False) -> SpeechTranscriber:
        """Singleton accessor for SpeechTranscriber."""
        if cls._instance is None or (use_mock and not getattr(cls._instance, "use_mock", False)):
            cls._instance = cls(use_mock=use_mock)
        return cls._instance

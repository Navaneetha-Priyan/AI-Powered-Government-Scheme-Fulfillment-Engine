"""Speech-to-Text service using Faster-Whisper (Phase 2/3.5 - Voice Assistant).

Phase 3.5 changes (Tamil ASR accuracy optimization):
- Explicitly recognize Tamil via ``language`` and ``task`` instead of relying on
  automatic language detection.
- Enable Faster-Whisper's built-in Silero VAD by default to better handle
  pauses, silence, and background noise.
- Use ``beam_size=5`` and ``condition_on_previous_text=False`` as code-level
  decoding defaults suited to short, single-utterance citizen queries.
- Configuration (model size, language, VAD) is env-driven via ``WHISPER_*``.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger
from app.exceptions.exceptions import AppException

logger = get_logger(__name__)


class SpeechToTextError(AppException):
    """Raised when audio transcription fails."""

    def __init__(self, reason: str = "Speech-to-text transcription failed"):
        super().__init__(reason, 500, "SPEECH_TO_TEXT_ERROR")


class SpeechToTextModelNotLoadedError(AppException):
    """Raised when the Whisper model is required but has not been loaded."""

    def __init__(self, reason: str = "Speech-to-text model is not loaded"):
        super().__init__(reason, 503, "SPEECH_TO_TEXT_MODEL_NOT_LOADED")


def _detect_device() -> str:
    """Return 'cuda' when a CUDA GPU is available, otherwise 'cpu'."""
    # Prefer CTranslate2's native CUDA detection (Faster-Whisper's runtime).
    try:
        import ctranslate2

        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except Exception:
        logger.debug("ctranslate2 CUDA detection unavailable; checking torch")

    # Fallback: torch CUDA availability.
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except Exception:
        logger.debug("torch CUDA detection unavailable; using CPU")

    return "cpu"


def _compute_type_for(device: str) -> str:
    """Choose the appropriate Faster-Whisper compute type for a device."""
    return "float16" if device == "cuda" else "int8"


class SpeechToTextService:
    """Transcribe audio files with a single, lazily-loaded Faster-Whisper model.

    The model is intended to be loaded exactly once at application startup via
    ``load_model()`` and then reused for every request. It is never reloaded
    per request.
    """

    def __init__(
        self,
        model_name: str = settings.WHISPER_MODEL,
        language: str = settings.WHISPER_LANGUAGE,
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
        vad_filter: bool = settings.WHISPER_VAD_FILTER,
        beam_size: int = 5,
        condition_on_previous_text: bool = False,
    ) -> None:
        self.model_name = model_name
        self.language = language
        self.device = device or _detect_device()
        self.compute_type = compute_type or _compute_type_for(self.device)
        self.vad_filter = vad_filter
        self.beam_size = beam_size
        self.condition_on_previous_text = condition_on_previous_text
        self._model = None
        logger.info(
            "SpeechToTextService configured "
            "(model=%s, language=%s, device=%s, compute_type=%s, "
            "vad_filter=%s, beam_size=%s, condition_on_previous_text=%s)",
            self.model_name,
            self.language,
            self.device,
            self.compute_type,
            self.vad_filter,
            self.beam_size,
            self.condition_on_previous_text,
        )

    @property
    def is_loaded(self) -> bool:
        """Whether the Whisper model has been loaded into memory."""
        return self._model is not None

    def load_model(self) -> None:
        """Load the Faster-Whisper model. Safe to call more than once."""
        if self._model is not None:
            return

        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            logger.error("faster-whisper is not installed: %s", exc)
            raise SpeechToTextModelNotLoadedError(
                "faster-whisper package is not installed. Run: pip install faster-whisper"
            ) from exc

        logger.info(
            "Loading Faster-Whisper model '%s' (device=%s, compute_type=%s)...",
            self.model_name,
            self.device,
            self.compute_type,
        )
        try:
            self._model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type,
            )
        except Exception as exc:
            logger.exception("Failed to load Faster-Whisper model")
            raise SpeechToTextModelNotLoadedError(f"Failed to load Whisper model: {exc}") from exc

        logger.info("Faster-Whisper model '%s' loaded successfully.", self.model_name)

    def transcribe(self, audio_path: str | Path) -> str:
        """Transcribe an audio file and return the recognized text.

        Tamil-specific decoding settings are passed explicitly so we never rely
        on automatic language detection for Tamil-only recordings:

        - ``language``/``task``: force Tamil transcription (not translation).
        - ``vad_filter``: enable Faster-Whisper's built-in Silero VAD to better
          handle pauses, silence, and background noise.
        - ``beam_size=5``: wider beam for more accurate decoding of short
          utterances.
        - ``condition_on_previous_text=False``: avoid hallucinated repetition
          on short, single-utterance citizen queries.
        """
        if self._model is None:
            self.load_model()

        try:
            segments, _info = self._model.transcribe(
                str(audio_path),
                language=self.language,
                task="transcribe",
                vad_filter=self.vad_filter,
                beam_size=self.beam_size,
                condition_on_previous_text=self.condition_on_previous_text,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            print("\n" + "=" * 60)
            print("🎤 WHISPER TRANSCRIPTION")
            print("=" * 60)
            print(text)
            print("=" * 60 + "\n")
        except Exception as exc:
            logger.exception("Transcription failed for %s", audio_path)
            raise SpeechToTextError(f"Transcription failed: {exc}") from exc

        logger.info("Transcribed %s -> %d characters", audio_path, len(text))
        return text


@lru_cache(maxsize=1)
def get_speech_to_text_service() -> SpeechToTextService:
    """Return the shared singleton SpeechToTextService instance."""
    return SpeechToTextService()

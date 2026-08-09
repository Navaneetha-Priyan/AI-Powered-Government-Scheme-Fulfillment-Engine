"""Unit tests for the SpeechToTextService (Phase 2/3.5 - Voice Assistant).

Phase 3.5 adds coverage for:
- Tamil language configuration (WHISPER_LANGUAGE=ta)
- transcription task (task="transcribe")
- VAD configuration (WHISPER_VAD_FILTER)
- beam_size=5
- condition_on_previous_text=False
- small/medium model selection
- environment configuration
- existing error handling

`WhisperModel` is always mocked; tests never download the real model.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.speech_to_text_service import (
    SpeechToTextModelNotLoadedError,
    SpeechToTextService,
    _compute_type_for,
    _detect_device,
)


class TestDeviceAndComputeType:
    def test_compute_type_cuda_is_float16(self):
        assert _compute_type_for("cuda") == "float16"

    def test_compute_type_cpu_is_int8(self):
        assert _compute_type_for("cpu") == "int8"

    def test_detect_device_uses_ctranslate2_cuda(self):
        fake_ct2 = SimpleNamespace(get_cuda_device_count=lambda: 2)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: False))
        with patch.dict("sys.modules", {"ctranslate2": fake_ct2, "torch": fake_torch}):
            assert _detect_device() == "cuda"

    def test_detect_device_falls_back_to_torch_cuda(self):
        def _no_ct2(*a, **k):
            raise ImportError("no ct2")

        fake_ct2 = SimpleNamespace(get_cuda_device_count=_no_ct2)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=lambda: True))
        with patch.dict("sys.modules", {"ctranslate2": fake_ct2, "torch": fake_torch}):
            assert _detect_device() == "cuda"

    def test_detect_device_falls_back_to_cpu(self):
        def _no_ct2(*a, **k):
            raise ImportError("no ct2")

        def _no_torch(*a, **k):
            raise ImportError("no torch")

        fake_ct2 = SimpleNamespace(get_cuda_device_count=_no_ct2)
        fake_torch = SimpleNamespace(cuda=SimpleNamespace(is_available=_no_torch))
        with patch.dict("sys.modules", {"ctranslate2": fake_ct2, "torch": fake_torch}):
            assert _detect_device() == "cpu"


class TestSpeechToTextService:
    def test_default_configuration(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.model_name == "medium"
        assert service.device == "cpu"
        assert service.compute_type == "int8"
        assert service.is_loaded is False

    def test_explicit_configuration(self):
        service = SpeechToTextService(model_name="small", device="cpu", compute_type="int8")
        assert service.model_name == "small"
        assert service.device == "cpu"
        assert service.compute_type == "int8"

    def test_load_model_raises_when_package_missing(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        with patch.dict("sys.modules", {"faster_whisper": None}):
            with pytest.raises(SpeechToTextModelNotLoadedError):
                service.load_model()

    def test_load_model_sets_model(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_whisper = SimpleNamespace(WhisperModel=lambda *a, **k: fake_model)
        with patch.dict("sys.modules", {"faster_whisper": fake_whisper}):
            service.load_model()
        assert service.is_loaded is True

    def test_load_model_is_idempotent(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        calls = {"count": 0}

        def _ctor(*args, **kwargs):
            calls["count"] += 1
            return fake_model

        fake_whisper = SimpleNamespace(WhisperModel=_ctor)
        with patch.dict("sys.modules", {"faster_whisper": fake_whisper}):
            service.load_model()
            service.load_model()
        assert calls["count"] == 1

    def test_transcribe_joins_segments(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (
            iter(
                [
                    SimpleNamespace(text="Hello"),
                    SimpleNamespace(text="world"),
                    SimpleNamespace(text=""),
                ]
            ),
            SimpleNamespace(language="ta"),
        )
        service._model = fake_model
        assert service.transcribe("/tmp/sample.wav") == "Hello world"

    def test_transcribe_auto_loads_model(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (
            iter([SimpleNamespace(text="Only one")]),
            SimpleNamespace(language="ta"),
        )
        fake_whisper = SimpleNamespace(WhisperModel=lambda *a, **k: fake_model)
        with patch.dict("sys.modules", {"faster_whisper": fake_whisper}):
            assert service.transcribe("/tmp/sample.wav") == "Only one"
        assert service.is_loaded is True

    def test_transcribe_raises_speech_to_text_error_on_failure(self):
        from app.services.speech_to_text_service import SpeechToTextError

        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_model.transcribe.side_effect = RuntimeError("boom")
        service._model = fake_model
        with pytest.raises(SpeechToTextError):
            service.transcribe("/tmp/sample.wav")


class TestTamilLanguageConfiguration:
    """Ensure Tamil is forced via language + transcribe task (no auto-detect)."""

    def test_default_language_is_tamil(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.language == "ta"

    def test_explicit_language_override(self):
        service = SpeechToTextService(language="en", device="cpu", compute_type="int8")
        assert service.language == "en"

    def test_transcribe_passes_language_and_task(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (
            iter([SimpleNamespace(text="வணக்கம்")]),
            SimpleNamespace(language="ta"),
        )
        service._model = fake_model
        service.transcribe("/tmp/sample.m4a")
        _, kwargs = fake_model.transcribe.call_args
        assert kwargs["language"] == "ta"
        assert kwargs["task"] == "transcribe"


class TestTranscriptionConfiguration:
    """Decoding parameters are code-level defaults (beam_size, conditioning)."""

    def test_beam_size_defaults_to_5(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.beam_size == 5

    def test_beam_size_is_configurable(self):
        service = SpeechToTextService(beam_size=8, device="cpu", compute_type="int8")
        assert service.beam_size == 8

    def test_condition_on_previous_text_defaults_false(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.condition_on_previous_text is False

    def test_transcribe_passes_beam_and_conditioning(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (
            iter([SimpleNamespace(text="உரை")]),
            SimpleNamespace(language="ta"),
        )
        service._model = fake_model
        service.transcribe("/tmp/sample.m4a")
        _, kwargs = fake_model.transcribe.call_args
        assert kwargs["beam_size"] == 5
        assert kwargs["condition_on_previous_text"] is False


class TestVADConfiguration:
    """VAD uses Faster-Whisper's built-in vad_filter flag."""

    def test_vad_filter_defaults_true(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.vad_filter is True

    def test_vad_filter_is_configurable(self):
        service = SpeechToTextService(vad_filter=False, device="cpu", compute_type="int8")
        assert service.vad_filter is False

    def test_transcribe_passes_vad_filter(self):
        service = SpeechToTextService(device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_model.transcribe.return_value = (
            iter([SimpleNamespace(text="உரை")]),
            SimpleNamespace(language="ta"),
        )
        service._model = fake_model
        service.transcribe("/tmp/sample.m4a")
        _, kwargs = fake_model.transcribe.call_args
        assert kwargs["vad_filter"] is True


class TestModelConfiguration:
    """Model size is configurable; medium is the default; small is supported."""

    def test_default_model_is_medium(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.model_name == "medium"

    def test_small_model_selection(self):
        service = SpeechToTextService(model_name="small", device="cpu", compute_type="int8")
        assert service.model_name == "small"

    def test_medium_model_selection(self):
        service = SpeechToTextService(model_name="medium", device="cpu", compute_type="int8")
        assert service.model_name == "medium"

    def test_model_passed_to_whisper_model(self):
        service = SpeechToTextService(model_name="medium", device="cpu", compute_type="int8")
        fake_model = MagicMock()
        fake_whisper = SimpleNamespace(WhisperModel=MagicMock(return_value=fake_model))
        with patch.dict("sys.modules", {"faster_whisper": fake_whisper}):
            service.load_model()
        fake_whisper.WhisperModel.assert_called_once_with(
            "medium", device="cpu", compute_type="int8"
        )


class TestEnvironmentConfiguration:
    """WHISPER_* env vars are honored by the Settings model."""

    def test_settings_expose_whisper_defaults(self):
        from app.core.config import settings as app_settings

        assert app_settings.WHISPER_MODEL == "medium"
        assert app_settings.WHISPER_LANGUAGE == "ta"
        assert app_settings.WHISPER_VAD_FILTER is True

    def test_invalid_whisper_model_rejected(self):
        from pydantic import ValidationError

        from app.core.config import Settings

        with patch.dict(
            "os.environ", {"WHISPER_MODEL": "large"}, clear=False
        ), pytest.raises((ValidationError, ValueError)):
            Settings()

    def test_service_uses_settings_defaults(self):
        with patch("app.services.speech_to_text_service._detect_device", return_value="cpu"):
            service = SpeechToTextService()
        assert service.model_name == "medium"
        assert service.language == "ta"
        assert service.vad_filter is True

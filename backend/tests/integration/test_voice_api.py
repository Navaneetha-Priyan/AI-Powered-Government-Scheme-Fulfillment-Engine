"""Integration tests for the /voice/transcribe endpoint (Phase 2 - Voice Assistant)."""
from __future__ import annotations

import io
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.services.speech_to_text_service import SpeechToTextService


@pytest.fixture(autouse=True)
def mock_speech_service(client: TestClient):
    """Replace the actual SpeechToTextService with a fake that is always loaded."""
    fake_service = MagicMock(spec=SpeechToTextService)
    fake_service.is_loaded = True
    fake_service.transcribe.return_value = "transcribed speech"
    client.app.state.speech_service = fake_service
    yield
    # Cleanup override
    client.app.state.speech_service = None


class TestVoiceTranscribeEndpoint:
    """Tests for POST /voice/transcribe"""

    AUDIO_CONTENT = b"\x00\x01\x02\x03" * 256  # 1 KB dummy audio

    def _audio_file(self, filename: str = "sample.m4a"):
        return io.BytesIO(self.AUDIO_CONTENT)

    def _transcribe(self, client: TestClient, auth_headers: dict, filename: str = "sample.m4a") -> tuple:
        """Helper: POST /voice/transcribe with a dummy audio file."""
        file = self._audio_file(filename)
        return client.post(
            "/voice/transcribe",
            files={"audio": (filename, file, "audio/mp4")},
            headers=auth_headers,
        )

    # ── Success cases ────────────────────────────────────────────────

    def test_transcribe_m4a_success(self, client: TestClient, auth_headers: dict):
        response = self._transcribe(client, auth_headers, "test.m4a")
        assert response.status_code == 200
        data = response.json()
        assert data == {"text": "transcribed speech"}

    def test_transcribe_wav_success(self, client: TestClient, auth_headers: dict):
        response = self._transcribe(client, auth_headers, "audio.wav")
        assert response.status_code == 200
        assert response.json() == {"text": "transcribed speech"}

    # ── Validation cases ─────────────────────────────────────────────

    def test_requires_authentication(self, client: TestClient):
        """Non-authenticated requests should be rejected with 401."""
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.m4a", io.BytesIO(b"dummy"), "audio/mp4")},
        )
        assert response.status_code == 401

    def test_rejects_invalid_extension(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.mp3", io.BytesIO(b"dummy"), "audio/mpeg")},
            headers=auth_headers,
        )
        assert response.status_code == 415

    def test_rejects_unsupported_content_type(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("test.m4a", io.BytesIO(b"dummy"), "video/mp4")},
            headers=auth_headers,
        )
        assert response.status_code == 415

    def test_rejects_no_filename(self, client: TestClient, auth_headers: dict):
        response = client.post(
            "/voice/transcribe",
            files={"audio": ("", io.BytesIO(b"dummy"), "audio/mp4")},
            headers=auth_headers,
        )
        # Starlette rejects empty filenames at the form level (422) before
        # our validation runs. Either 400 or 422 is acceptable.
        assert response.status_code in (400, 422)

    # ── Error cases ──────────────────────────────────────────────────

    def test_model_not_loaded_returns_503(self, client: TestClient, auth_headers: dict):
        client.app.state.speech_service.is_loaded = False
        response = self._transcribe(client, auth_headers)
        assert response.status_code == 503
        data = response.json()
        assert "SPEECH_TO_TEXT_MODEL_NOT_LOADED" in str(data)

    def test_transcription_failure_returns_500(self, client: TestClient, auth_headers: dict):
        from app.services.speech_to_text_service import SpeechToTextError

        client.app.state.speech_service.transcribe.side_effect = SpeechToTextError("transcription failed")
        response = self._transcribe(client, auth_headers)
        assert response.status_code == 500
        data = response.json()
        assert "SPEECH_TO_TEXT_ERROR" in str(data)

"""Tests for runtime/voice_interface.py — voice interface."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from runtime.voice_interface import VoiceConfig, VoiceInterface


class TestVoiceConfig:
    """Tests for VoiceConfig."""

    def test_defaults(self) -> None:
        c = VoiceConfig()
        assert c.enabled is True
        assert c.tts_rate == 180
        assert c.language == "en"

    def test_custom(self) -> None:
        c = VoiceConfig(enabled=False, tts_rate=200, language="ar")
        assert c.enabled is False
        assert c.tts_rate == 200
        assert c.language == "ar"


class TestVoiceInterface:
    """Tests for VoiceInterface."""

    def test_init_default_config(self) -> None:
        vi = VoiceInterface()
        assert vi.config.enabled is True

    def test_init_custom_config(self) -> None:
        vi = VoiceInterface(VoiceConfig(enabled=False))
        assert vi.config.enabled is False

    def test_speak_disabled(self) -> None:
        vi = VoiceInterface(VoiceConfig(enabled=False))
        assert vi.speak("hello") is False

    def test_speak_empty_text(self) -> None:
        vi = VoiceInterface()
        # Even if TTS is available, empty text should return False
        vi._tts_available = True
        assert vi.speak("") is False
        assert vi.speak("   ") is False

    def test_speak_no_tts_available(self) -> None:
        vi = VoiceInterface()
        vi._tts_available = False
        assert vi.speak("hello") is False

    def test_speak_windows_success(self) -> None:
        vi = VoiceInterface()
        vi._platform = "windows"
        vi._tts_available = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert vi.speak("hello world") is True

    def test_speak_windows_failure(self) -> None:
        vi = VoiceInterface()
        vi._platform = "windows"
        vi._tts_available = True
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            assert vi.speak("hello") is False

    def test_speak_macos_success(self) -> None:
        vi = VoiceInterface()
        vi._platform = "darwin"
        vi._tts_available = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert vi.speak("hello") is True

    def test_speak_macos_with_voice(self) -> None:
        vi = VoiceInterface(VoiceConfig(tts_voice="Alex"))
        vi._platform = "darwin"
        vi._tts_available = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            vi.speak("hello")
            # Check that -v Alex was passed
            args = mock_run.call_args[0][0]
            assert "-v" in args
            assert "Alex" in args

    def test_speak_linux_espeak(self) -> None:
        vi = VoiceInterface()
        vi._platform = "linux"
        vi._tts_available = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result), \
             patch("shutil.which", return_value="/usr/bin/espeak"):
            assert vi.speak("hello") is True

    def test_speak_linux_festival(self) -> None:
        vi = VoiceInterface()
        vi._platform = "linux"
        vi._tts_available = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result), \
             patch("shutil.which", side_effect=lambda x: "/usr/bin/festival" if x == "festival" else None):
            assert vi.speak("hello") is True

    def test_speak_subprocess_error(self) -> None:
        vi = VoiceInterface()
        vi._platform = "darwin"
        vi._tts_available = True
        with patch("subprocess.run", side_effect=subprocess.SubprocessError("fail")):
            assert vi.speak("hello") is False

    def test_listen_disabled(self) -> None:
        vi = VoiceInterface(VoiceConfig(enabled=False))
        assert vi.listen() is None

    def test_listen_no_stt(self) -> None:
        vi = VoiceInterface()
        vi._stt_available = False
        assert vi.listen() is None

    def test_listen_windows_success(self) -> None:
        vi = VoiceInterface()
        vi._platform = "windows"
        vi._stt_available = True
        mock_result = MagicMock()
        mock_result.stdout = "hello world\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = vi.listen()
            assert result == "hello world"

    def test_listen_windows_empty(self) -> None:
        vi = VoiceInterface()
        vi._platform = "windows"
        vi._stt_available = True
        mock_result = MagicMock()
        mock_result.stdout = "\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            assert vi.listen() is None

    def test_listen_macos_success(self) -> None:
        vi = VoiceInterface()
        vi._platform = "darwin"
        vi._stt_available = True
        mock_result = MagicMock()
        mock_result.stdout = "voice command\n"
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            result = vi.listen()
            assert result == "voice command"

    def test_listen_subprocess_error(self) -> None:
        vi = VoiceInterface()
        vi._platform = "darwin"
        vi._stt_available = True
        with patch("subprocess.run", side_effect=subprocess.SubprocessError("fail")):
            assert vi.listen() is None

    def test_speak_async_macos(self) -> None:
        vi = VoiceInterface()
        vi._platform = "darwin"
        vi._tts_available = True
        mock_proc = MagicMock()
        with patch("subprocess.Popen", return_value=mock_proc):
            result = vi.speak_async("hello")
            assert result is mock_proc

    def test_speak_async_disabled(self) -> None:
        vi = VoiceInterface(VoiceConfig(enabled=False))
        assert vi.speak_async("hello") is None

    def test_speak_async_empty(self) -> None:
        vi = VoiceInterface()
        vi._tts_available = True
        assert vi.speak_async("") is None

    def test_status(self) -> None:
        vi = VoiceInterface()
        status = vi.status()
        assert "platform" in status
        assert "tts_available" in status
        assert "stt_available" in status
        assert "enabled" in status
        assert "language" in status

    def test_tts_available_property(self) -> None:
        vi = VoiceInterface()
        vi._tts_available = True
        assert vi.tts_available is True

    def test_stt_available_property(self) -> None:
        vi = VoiceInterface()
        vi._stt_available = False
        assert vi.stt_available is False

"""Tests for runtime/voice_interface.py — voice interface."""

from __future__ import annotations

import subprocess
from pathlib import Path
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

    # --- _check_tts branch coverage ---

    def test_check_tts_windows_exception(self) -> None:
        """Windows TTS check returns False when ctypes.windll raises."""
        mock_ctypes = MagicMock()
        del mock_ctypes.windll  # accessing raises AttributeError
        with patch.dict("sys.modules", {"ctypes": mock_ctypes}), \
             patch("platform.system", return_value="Windows"):
            vi = VoiceInterface()
            assert vi._tts_available is False

    def test_check_tts_darwin_available(self) -> None:
        """Darwin TTS check returns True when 'say' is found."""
        with patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/say"):
            vi = VoiceInterface()
            assert vi._tts_available is True

    def test_check_tts_darwin_unavailable(self) -> None:
        """Darwin TTS check returns False when 'say' is not found."""
        with patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value=None):
            vi = VoiceInterface()
            assert vi._tts_available is False

    def test_check_tts_linux_espeak(self) -> None:
        """Linux TTS check returns True when espeak is found."""
        with patch("platform.system", return_value="Linux"), \
             patch("shutil.which", side_effect=lambda x: "/usr/bin/espeak" if x == "espeak" else None):
            vi = VoiceInterface()
            assert vi._tts_available is True

    def test_check_tts_linux_festival(self) -> None:
        """Linux TTS check returns True when festival is found."""
        with patch("platform.system", return_value="Linux"), \
             patch("shutil.which", side_effect=lambda x: "/usr/bin/festival" if x == "festival" else None):
            vi = VoiceInterface()
            assert vi._tts_available is True

    def test_check_tts_linux_unavailable(self) -> None:
        """Linux TTS check returns False when neither espeak nor festival found."""
        with patch("platform.system", return_value="Linux"), \
             patch("shutil.which", return_value=None):
            vi = VoiceInterface()
            assert vi._tts_available is False

    # --- _check_stt branch coverage ---

    def test_check_stt_darwin_available(self) -> None:
        """Darwin STT check returns True when osascript is found."""
        with patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value="/usr/bin/osascript"):
            vi = VoiceInterface()
            assert vi._stt_available is True

    def test_check_stt_darwin_unavailable(self) -> None:
        """Darwin STT check returns False when osascript is not found."""
        with patch("platform.system", return_value="Darwin"), \
             patch("shutil.which", return_value=None):
            vi = VoiceInterface()
            assert vi._stt_available is False

    def test_check_stt_linux_unavailable(self) -> None:
        """Linux STT check returns False (not supported via stdlib)."""
        with patch("platform.system", return_value="Linux"):
            vi = VoiceInterface()
            assert vi._stt_available is False

    # --- _speak_linux edge case ---

    def test_speak_linux_no_engine(self) -> None:
        """Linux speak returns False when no TTS engine is available."""
        vi = VoiceInterface()
        vi._platform = "linux"
        vi._tts_available = True
        with patch("shutil.which", return_value=None):
            assert vi.speak("hello") is False

    # --- listen Linux ---

    def test_listen_linux_returns_none(self) -> None:
        """Linux listen returns None (STT not supported via stdlib)."""
        vi = VoiceInterface()
        vi._platform = "linux"
        vi._stt_available = True
        assert vi.listen() is None

    # --- speak_async branches ---

    def test_speak_async_linux_espeak(self) -> None:
        """speak_async on Linux with espeak returns a Popen process."""
        vi = VoiceInterface()
        vi._platform = "linux"
        vi._tts_available = True
        mock_proc = MagicMock()
        with patch("shutil.which", return_value="/usr/bin/espeak"), \
             patch("subprocess.Popen", return_value=mock_proc):
            result = vi.speak_async("hello")
            assert result is mock_proc

    def test_speak_async_windows_fallback(self) -> None:
        """speak_async on Windows falls back to sync speak and returns None."""
        vi = VoiceInterface()
        vi._platform = "windows"
        vi._tts_available = True
        with patch.object(vi, "speak", return_value=True) as mock_speak:
            result = vi.speak_async("hello")
            assert result is None
            mock_speak.assert_called_once_with("hello")

    def test_speak_async_linux_no_espeak(self) -> None:
        """speak_async on Linux without espeak falls back to sync."""
        vi = VoiceInterface()
        vi._platform = "linux"
        vi._tts_available = True
        with patch("shutil.which", return_value=None), \
             patch.object(vi, "speak", return_value=True) as mock_speak:
            result = vi.speak_async("hello")
            assert result is None
            mock_speak.assert_called_once_with("hello")

    # --- __main__ block ---

    def test_main_block(self, capsys) -> None:
        """Exercise the __main__ block of voice_interface.py."""
        source = Path(__file__).resolve().parent.parent / "voice_interface.py"
        code = source.read_text(encoding="utf-8")
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result):
            exec(compile(code, str(source), "exec"), {"__name__": "__main__"})
        out = capsys.readouterr().out
        assert "TTS:" in out
        assert "STT:" in out

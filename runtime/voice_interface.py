#!/usr/bin/env python3
"""Voice interface for AI Global OS.

Provides speech-to-text for voice commands and text-to-speech for
agent responses. Uses the OS-native speech APIs when available:

- **Windows:** SAPI (System.Speech) via subprocess
- **macOS:** `say` and `osascript` commands
- **Linux:** `espeak` or `festival` if installed

All voice features are optional — the system gracefully degrades when
speech tools are not available.

Usage::

    from runtime.voice_interface import VoiceInterface
    vi = VoiceInterface()
    text = vi.listen()  # STT: listen for voice input
    vi.speak("Task completed successfully")  # TTS: speak a response
"""

from __future__ import annotations

import platform
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass
class VoiceConfig:
    """Configuration for the voice interface."""

    enabled: bool = True
    tts_rate: int = 180  # words per minute
    tts_voice: str = ""  # empty = system default
    stt_timeout: int = 10  # seconds
    language: str = "en"


class VoiceInterface:
    """Cross-platform voice interface for AI Global OS."""

    def __init__(self, config: VoiceConfig | None = None) -> None:
        self.config = config or VoiceConfig()
        self._platform = platform.system().lower()
        self._tts_available = self._check_tts()
        self._stt_available = self._check_stt()

    def _check_tts(self) -> bool:
        """Check if text-to-speech is available."""
        if self._platform == "windows":
            try:
                import ctypes
                return ctypes.windll is not None  # SAPI available via COM
            except (OSError, AttributeError):
                return False
        if self._platform == "darwin":
            return shutil.which("say") is not None
        # Linux
        return shutil.which("espeak") is not None or shutil.which("festival") is not None

    def _check_stt(self) -> bool:
        """Check if speech-to-text is available."""
        if self._platform == "windows":
            try:
                return True  # SAPI recognition available
            except (OSError, AttributeError):  # pragma: no cover
                return False  # pragma: no cover
        if self._platform == "darwin":
            return shutil.which("osascript") is not None
        # Linux — would need pocketsphinx or similar
        return False

    @property
    def tts_available(self) -> bool:
        """Whether text-to-speech is available."""
        return self._tts_available

    @property
    def stt_available(self) -> bool:
        """Whether speech-to-text is available."""
        return self._stt_available

    def speak(self, text: str) -> bool:
        """Speak text using text-to-speech.

        Args:
            text: The text to speak.

        Returns:
            True if speech was produced, False if TTS unavailable.
        """
        if not self.config.enabled or not self._tts_available:
            return False
        if not text.strip():
            return False
        try:
            if self._platform == "windows":
                return self._speak_windows(text)
            if self._platform == "darwin":
                return self._speak_macos(text)
            return self._speak_linux(text)
        except (OSError, subprocess.SubprocessError):
            return False

    def _speak_windows(self, text: str) -> bool:
        """Speak using Windows SAPI via PowerShell."""
        # Escape single quotes for PowerShell
        escaped = text.replace("'", "''")
        ps_script = (
            f"Add-Type -AssemblyName System.Speech; "
            f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
            f"$s.Rate = {self.config.tts_rate - 180}; "
            f"$s.Speak('{escaped}')"
        )
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            timeout=30,
        )
        return result.returncode == 0

    def _speak_macos(self, text: str) -> bool:
        """Speak using macOS `say` command."""
        cmd = ["say"]
        if self.config.tts_voice:
            cmd.extend(["-v", self.config.tts_voice])
        cmd.append(text)
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        return result.returncode == 0

    def _speak_linux(self, text: str) -> bool:
        """Speak using espeak or festival."""
        if shutil.which("espeak"):
            espeak_result = subprocess.run(
                ["espeak", "-s", str(self.config.tts_rate), text],
                capture_output=True,
                timeout=30,
            )
            return espeak_result.returncode == 0
        if shutil.which("festival"):
            festival_result = subprocess.run(
                ["festival", "--tts"],
                input=text,
                text=True,
                capture_output=True,
                timeout=30,
            )
            return festival_result.returncode == 0
        return False

    def listen(self) -> str | None:
        """Listen for voice input and return transcribed text.

        Returns:
            Transcribed text, or None if STT unavailable or failed.
        """
        if not self.config.enabled or not self._stt_available:
            return None
        try:
            if self._platform == "windows":
                return self._listen_windows()
            if self._platform == "darwin":
                return self._listen_macos()
            return None  # Linux STT not supported via stdlib
        except (OSError, subprocess.SubprocessError):
            return None

    def _listen_windows(self) -> str | None:
        """Listen using Windows SAPI speech recognition."""
        ps_script = (
            "Add-Type -AssemblyName System.Speech; "
            "$r = New-Object System.Speech.Recognition.SpeechRecognitionEngine; "
            "$r.SetInputToDefaultAudioDevice(); "
            "$g = New-Object System.Speech.Recognition.DictationGrammar; "
            "$r.LoadGrammar($g); "
            f"$result = $r.Recognize([TimeSpan]::FromSeconds({self.config.stt_timeout})); "
            "if ($result) { $result.Text } else { '' }"
        )
        result = subprocess.run(
            ["powershell", "-Command", ps_script],
            capture_output=True,
            text=True,
            timeout=self.config.stt_timeout + 5,
        )
        text = result.stdout.strip()
        return text if text else None

    def _listen_macos(self) -> str | None:
        """Listen using macOS osascript."""
        script = (
            'set userInput to text returned of (display dialog '
            '"Speak your command:" default answer "" with title "AI Global OS Voice Input")'
        )
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=self.config.stt_timeout + 5,
        )
        text = result.stdout.strip()
        return text if text else None

    def speak_async(self, text: str) -> subprocess.Popen[bytes] | None:
        """Speak text asynchronously (non-blocking).

        Returns the process handle or None if TTS unavailable.
        """
        if not self.config.enabled or not self._tts_available:
            return None
        if not text.strip():
            return None
        if self._platform == "darwin":
            return subprocess.Popen(["say", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if self._platform == "linux" and shutil.which("espeak"):
            return subprocess.Popen(["espeak", text], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Windows: no easy async via PowerShell
        self.speak(text)  # fallback to sync
        return None

    def status(self) -> dict[str, Any]:
        """Return voice interface status."""
        return {
            "platform": self._platform,
            "tts_available": self._tts_available,
            "stt_available": self._stt_available,
            "enabled": self.config.enabled,
            "language": self.config.language,
        }


if __name__ == "__main__":
    vi = VoiceInterface()
    print(f"TTS: {'available' if vi.tts_available else 'not available'}")
    print(f"STT: {'available' if vi.stt_available else 'not available'}")
    if vi.tts_available:
        vi.speak("AI Global OS voice interface is ready.")

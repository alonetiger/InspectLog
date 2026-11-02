"""Audio tone generator for speaker channel separation diagnostics."""

from __future__ import annotations

import io
import math
import struct
import sys
import wave

from hardwareverify.infra.logging import get_logger

logger = get_logger("audio_tone_generator")


def generate_stereo_wav(
    freq: float = 440.0,
    duration: float = 1.2,
    sample_rate: int = 44100,
    left: bool = True,
    right: bool = False,
    volume: float = 0.85,
) -> bytes:
    """Generate in-memory 16-bit PCM stereo WAV audio with channel isolation.

    Args:
        freq: Frequency in Hertz (default: 440 Hz / Concert A).
        duration: Duration in seconds.
        sample_rate: Sampling frequency in Hz.
        left: Whether sound is played in the left audio channel.
        right: Whether sound is played in the right audio channel.
        volume: Peak amplitude scalar between 0.0 and 1.0.

    Returns:
        Raw bytes of a valid WAV audio container.
    """
    n_samples = int(sample_rate * duration)
    max_amp = int(32767 * max(0.0, min(1.0, volume)))

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(2)      # Stereo
        wav.setsampwidth(2)      # 16-bit
        wav.setframerate(sample_rate)

        # Apply smooth attack and release envelope (50ms) to avoid acoustic popping
        fade_samples = int(sample_rate * 0.05)
        frames = bytearray()

        for i in range(n_samples):
            # Sine wave sample
            t = i / sample_rate
            raw_sample = math.sin(2.0 * math.pi * freq * t)

            # Envelope scaling
            env = 1.0
            if i < fade_samples:
                env = i / fade_samples
            elif i > n_samples - fade_samples:
                env = (n_samples - i) / fade_samples

            sample_val = int(raw_sample * max_amp * env)
            l_val = sample_val if left else 0
            r_val = sample_val if right else 0

            frames.extend(struct.pack("<hh", l_val, r_val))

        wav.writeframes(frames)

    return buf.getvalue()


def play_channel_tone(left: bool, right: bool, freq: float = 440.0, duration: float = 1.2) -> bool:
    """Play a channel-isolated stereo tone asynchronously.

    Returns True if playback was initiated successfully.
    """
    wav_bytes = generate_stereo_wav(freq=freq, duration=duration, left=left, right=right)

    if sys.platform == "win32":
        try:
            import winsound
            winsound.PlaySound(
                wav_bytes,
                winsound.SND_MEMORY | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return True
        except Exception as e:
            logger.warning("winsound PlaySound failed: %s", e)

    # PySide6 fallback via QSoundEffect
    try:
        from PySide6.QtCore import QByteArray
        from PySide6.QtMultimedia import QSoundEffect
        # Create temp sound effect
        effect = QSoundEffect()
        qba = QByteArray(wav_bytes)
        effect.setData(qba)
        effect.play()
        return True
    except Exception as e:
        logger.warning("QtMultimedia QSoundEffect failed: %s", e)

    return False

"""Unit tests for stereo audio tone generation and channel isolation."""

import struct
import wave
import io
import pytest

from hardwareverify.ui.interactive.audio_tone_generator import generate_stereo_wav


def test_generate_stereo_wav_valid_container():
    """Verify generated WAV conforms to valid 16-bit 44.1kHz stereo format."""
    data = generate_stereo_wav(freq=440.0, duration=0.5, sample_rate=44100, left=True, right=False)
    assert len(data) > 44  # WAV header is 44 bytes

    with wave.open(io.BytesIO(data), "rb") as wav:
        assert wav.getnchannels() == 2
        assert wav.getsampwidth() == 2  # 16-bit
        assert wav.getframerate() == 44100
        assert wav.getnframes() == int(44100 * 0.5)


def test_left_channel_isolation():
    """Verify left-only tone produces non-zero on left and strictly zero on right."""
    data = generate_stereo_wav(freq=440.0, duration=0.1, sample_rate=44100, left=True, right=False)

    with wave.open(io.BytesIO(data), "rb") as wav:
        raw_frames = wav.readframes(wav.getnframes())

    n_samples = len(raw_frames) // 4
    unpacked = struct.unpack(f"<{n_samples * 2}h", raw_frames)

    left_samples = unpacked[0::2]
    right_samples = unpacked[1::2]

    # Right channel must be absolute silence
    assert all(r == 0 for r in right_samples)

    # Left channel must contain signal
    assert max(abs(l) for l in left_samples) > 5000


def test_right_channel_isolation():
    """Verify right-only tone produces non-zero on right and strictly zero on left."""
    data = generate_stereo_wav(freq=440.0, duration=0.1, sample_rate=44100, left=False, right=True)

    with wave.open(io.BytesIO(data), "rb") as wav:
        raw_frames = wav.readframes(wav.getnframes())

    n_samples = len(raw_frames) // 4
    unpacked = struct.unpack(f"<{n_samples * 2}h", raw_frames)

    left_samples = unpacked[0::2]
    right_samples = unpacked[1::2]

    # Left channel must be absolute silence
    assert all(l == 0 for l in left_samples)

    # Right channel must contain signal
    assert max(abs(r) for r in right_samples) > 5000

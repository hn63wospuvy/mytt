"""Tests for TTS adapters — silence PCM, VieNeu request, mock end-to-end (spec §4.2)."""

from livekit.agents import tts

from tutor_agent.tts.mock import MockTTS, pcm16_silence
from tutor_agent.tts.vieneu import build_vieneu_request


def test_pcm16_silence_length_mono_16bit():
    # 100 ms @ 24 kHz mono 16-bit = 2400 samples * 2 bytes
    data = pcm16_silence(duration_ms=100, sample_rate=24000)
    assert len(data) == 2400 * 2
    assert set(data) == {0}


def test_pcm16_silence_scales_with_rate():
    assert len(pcm16_silence(duration_ms=100, sample_rate=16000)) == 1600 * 2


def test_build_vieneu_request_includes_text_and_voice():
    body = build_vieneu_request("Xin chào", voice="v1")
    assert body["text"] == "Xin chào"
    assert body["voice"] == "v1"


def test_mock_tts_capabilities_and_rate():
    t = MockTTS()
    assert t.sample_rate == 24000
    assert t.num_channels == 1


async def test_mock_tts_synthesize_yields_audio_frames():
    t = MockTTS()
    frames = []
    async for ev in t.synthesize("hello world"):
        assert isinstance(ev, tts.SynthesizedAudio)
        frames.append(ev.frame)
    assert frames, "expected at least one audio frame"
    total_samples = sum(f.samples_per_channel for f in frames)
    assert total_samples > 0
    assert frames[0].sample_rate == 24000

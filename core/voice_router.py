"""
ContextForge — Voice Router
Handles Text-to-Speech and Speech-to-Text across multiple backends.
Mirrors the LLM router pattern — one interface, swappable backends.

Supported TTS backends: elevenlabs, openai, pyttsx3, custom
Supported STT backends: whisper_api, whisper_local, custom

Usage:
    from voice_router import VoiceRouter
    router = VoiceRouter(config)
    await router.speak("Well. Here we are again.")
    text = await router.listen()
"""

import os
import io
import asyncio
import tempfile
from typing import Optional


# ── TTS Backends ───────────────────────────────────────────────────────────────

async def _tts_elevenlabs(text: str, config: dict) -> bytes:
    """ElevenLabs — best quality. Needs ELEVENLABS_API_KEY."""
    try:
        import httpx
        api_key = os.environ.get(config.get("api_key_env", "ELEVENLABS_API_KEY"))
        voice_id = config.get("voice_id", "onwK4e9ZLuTAKqWW03F9")  # "Daniel" — warm, measured
        model_id = config.get("model_id", "eleven_monolingual_v1")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key":   api_key,
            "Content-Type": "application/json",
        }
        payload = {
            "text":     text,
            "model_id": model_id,
            "voice_settings": {
                "stability":        config.get("stability", 0.45),
                "similarity_boost": config.get("similarity_boost", 0.75),
                "style":            config.get("style", 0.35),
                "use_speaker_boost": True,
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=15.0)
            response.raise_for_status()
            return response.content

    except ImportError:
        raise RuntimeError("httpx not installed. Run: pip install httpx")


async def _tts_openai(text: str, config: dict) -> bytes:
    """OpenAI TTS — great quality, same key as LLM if using OpenAI backend."""
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"))
        )
        response = await client.audio.speech.create(
            model=config.get("model", "tts-1-hd"),
            voice=config.get("voice", "onyx"),       # onyx — deep, authoritative
            input=text,
            speed=config.get("speed", 0.95),
        )
        return response.content

    except ImportError:
        raise RuntimeError("openai not installed. Run: pip install openai")


async def _tts_pyttsx3(text: str, config: dict) -> bytes:
    """
    pyttsx3 — local, offline, no API needed.
    Sounds robotic. Free. Works everywhere.
    Saves to a temp file and returns bytes.
    """
    try:
        import pyttsx3
        import wave

        engine = pyttsx3.init()
        engine.setProperty("rate",   config.get("rate", 165))
        engine.setProperty("volume", config.get("volume", 1.0))

        voice_index = config.get("voice_index", 0)
        voices = engine.getProperty("voices")
        if voices and voice_index < len(voices):
            engine.setProperty("voice", voices[voice_index].id)

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        engine.save_to_file(text, tmp_path)
        engine.runAndWait()

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()

        os.unlink(tmp_path)
        return audio_bytes

    except ImportError:
        raise RuntimeError("pyttsx3 not installed. Run: pip install pyttsx3")


async def _tts_custom(text: str, config: dict) -> bytes:
    """Custom TTS endpoint — POST text, receive audio bytes."""
    try:
        import httpx
        url = config.get("custom_tts_endpoint")
        if not url:
            raise ValueError("'custom_tts_endpoint' not set in config")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={"text": text},
                timeout=15.0
            )
            response.raise_for_status()
            return response.content

    except ImportError:
        raise RuntimeError("httpx not installed. Run: pip install httpx")


TTS_BACKENDS = {
    "elevenlabs": _tts_elevenlabs,
    "openai":     _tts_openai,
    "pyttsx3":    _tts_pyttsx3,
    "custom":     _tts_custom,
}


# ── STT Backends ───────────────────────────────────────────────────────────────

async def _stt_whisper_api(audio_bytes: bytes, config: dict) -> str:
    """OpenAI Whisper API — accurate, fast, costs a tiny amount per minute."""
    try:
        import openai
        client = openai.AsyncOpenAI(
            api_key=os.environ.get(config.get("api_key_env", "OPENAI_API_KEY"))
        )
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"

        transcript = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=config.get("language", "en"),
        )
        return transcript.text.strip()

    except ImportError:
        raise RuntimeError("openai not installed. Run: pip install openai")


async def _stt_whisper_local(audio_bytes: bytes, config: dict) -> str:
    """
    Local Whisper — runs on your machine, no API cost, slower.
    Requires: pip install openai-whisper
    First run downloads the model (~140MB for 'base').
    """
    try:
        import whisper
        import numpy as np
        import soundfile as sf

        model_name = config.get("whisper_model", "base")

        # Load model — cached after first run
        model = whisper.load_model(model_name)

        # Decode audio bytes to numpy array
        audio_io = io.BytesIO(audio_bytes)
        audio_data, sample_rate = sf.read(audio_io)

        # Whisper expects float32 mono at 16kHz
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1)
        audio_data = audio_data.astype(np.float32)

        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: model.transcribe(audio_data, language=config.get("language", "en"))
        )
        return result["text"].strip()

    except ImportError:
        raise RuntimeError(
            "whisper not installed. Run: pip install openai-whisper soundfile"
        )


async def _stt_custom(audio_bytes: bytes, config: dict) -> str:
    """Custom STT endpoint — POST audio bytes, receive transcript."""
    try:
        import httpx
        url = config.get("custom_stt_endpoint")
        if not url:
            raise ValueError("'custom_stt_endpoint' not set in config")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=audio_bytes,
                headers={"Content-Type": "audio/wav"},
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("text", "").strip()

    except ImportError:
        raise RuntimeError("httpx not installed. Run: pip install httpx")


STT_BACKENDS = {
    "whisper_api":   _stt_whisper_api,
    "whisper_local": _stt_whisper_local,
    "custom":        _stt_custom,
}


# ── Audio Playback ─────────────────────────────────────────────────────────────

def play_audio(audio_bytes: bytes):
    """
    Play audio bytes through the system speaker.
    Uses pygame for reliable cross-platform playback.
    Falls back to playsound if pygame isn't available.
    """
    try:
        import pygame
        import io as _io

        pygame.mixer.init()
        sound = pygame.mixer.Sound(_io.BytesIO(audio_bytes))
        sound.play()

        # Wait for playback to finish
        while pygame.mixer.get_busy():
            pygame.time.wait(50)

    except ImportError:
        try:
            import playsound
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name
            playsound.playsound(tmp_path)
            os.unlink(tmp_path)
        except ImportError:
            raise RuntimeError(
                "No audio playback library found. "
                "Run: pip install pygame   (recommended)\n"
                "  or: pip install playsound"
            )


# ── Audio Recording ────────────────────────────────────────────────────────────

def record_until_silence(
    silence_threshold: float = 0.01,
    silence_duration:  float = 1.5,
    sample_rate:       int   = 16000,
    max_duration:      float = 30.0,
) -> bytes:
    """
    Record from microphone until the player stops talking.
    Returns raw WAV bytes.

    Silence detection: stops recording after silence_duration seconds
    of audio below silence_threshold amplitude.
    """
    try:
        import sounddevice as sd
        import soundfile as sf
        import numpy as np

        frames         = []
        silent_frames  = 0
        silence_limit  = int(silence_duration * sample_rate / 1024)
        max_frames     = int(max_duration * sample_rate / 1024)

        with sd.InputStream(samplerate=sample_rate, channels=1, dtype="float32", blocksize=1024) as stream:
            for _ in range(max_frames):
                frame, _ = stream.read(1024)
                frames.append(frame.copy())

                amplitude = np.abs(frame).mean()
                if amplitude < silence_threshold:
                    silent_frames += 1
                    if silent_frames >= silence_limit:
                        break
                else:
                    silent_frames = 0

        audio = np.concatenate(frames, axis=0)

        buf = io.BytesIO()
        sf.write(buf, audio, sample_rate, format="WAV")
        return buf.getvalue()

    except ImportError:
        raise RuntimeError(
            "Audio recording libraries not found. "
            "Run: pip install sounddevice soundfile"
        )


# ── Voice Router ───────────────────────────────────────────────────────────────

class VoiceRouter:
    def __init__(self, config: dict):
        voice_config = config.get("voice", {})

        self.tts_enabled  = voice_config.get("tts_enabled", True)
        self.stt_enabled  = voice_config.get("stt_enabled", True)
        self.tts_backend  = voice_config.get("tts_backend", "elevenlabs")
        self.stt_backend  = voice_config.get("stt_backend", "whisper_api")
        self.tts_config   = voice_config.get("tts", {})
        self.stt_config   = voice_config.get("stt", {})

        if self.tts_enabled and self.tts_backend not in TTS_BACKENDS:
            raise ValueError(
                f"Unknown TTS backend '{self.tts_backend}'. "
                f"Choose from: {list(TTS_BACKENDS.keys())}"
            )

        if self.stt_enabled and self.stt_backend not in STT_BACKENDS:
            raise ValueError(
                f"Unknown STT backend '{self.stt_backend}'. "
                f"Choose from: {list(STT_BACKENDS.keys())}"
            )

    async def speak(self, text: str) -> None:
        """Convert text to speech and play it."""
        if not self.tts_enabled or not text:
            return

        handler     = TTS_BACKENDS[self.tts_backend]
        audio_bytes = await handler(text, self.tts_config)
        play_audio(audio_bytes)

    async def listen(self) -> Optional[str]:
        """Record until silence, transcribe, return text."""
        if not self.stt_enabled:
            return None

        audio_bytes = record_until_silence(
            silence_threshold=self.stt_config.get("silence_threshold", 0.01),
            silence_duration=self.stt_config.get("silence_duration", 1.5),
        )

        if not audio_bytes:
            return None

        handler = STT_BACKENDS[self.stt_backend]
        return await handler(audio_bytes, self.stt_config)

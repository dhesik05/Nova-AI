from __future__ import annotations

import io
import logging
import os
from typing import BinaryIO, Optional

logger = logging.getLogger(__name__)

# Lazy-loaded global to avoid model load on import.
_model = None
_whisper_available: bool | None = None


def _whisper_ok() -> bool:
    global _whisper_available
    if _whisper_available is None:
        try:
            import faster_whisper  # noqa: F401
            _whisper_available = True
        except ImportError:
            _whisper_available = False
            logger.warning(
                "faster-whisper not installed. Speech-to-text disabled. "
                "Install with: pip install faster-whisper"
            )
    return _whisper_available


def _get_model():
    """
    Lazily create the Faster-Whisper model.

    Using a small default is better for local/dev on Windows; production users can
    override by setting the environment variable:
      FASTER_WHISPER_MODEL_SIZE (e.g. "base", "small", "medium")
    """
    global _model
    if not _whisper_ok():
        raise RuntimeError(
            "faster-whisper is not installed. "
            "Run: pip install faster-whisper"
        )
    if _model is None:
        from faster_whisper import WhisperModel
        size = os.environ.get("FASTER_WHISPER_MODEL_SIZE", "base")
        compute_type = os.environ.get("FASTER_WHISPER_COMPUTE_TYPE", "int8")
        logger.info("Loading Faster-Whisper model size=%s compute_type=%s", size, compute_type)
        _model = WhisperModel(model_size=size, compute_type=compute_type)
    return _model


def transcribe_audio(file: BinaryIO, language: str = "en") -> str:
    """
    Transcribe an uploaded audio file.

    Args:
        file: A binary file-like object (e.g. Starlette UploadFile.file)
        language: ISO language code, or "en".

    Returns:
        The concatenated transcription text.

    Raises:
        ValueError: for empty/invalid input
        RuntimeError: for transcription failures with descriptive messages
    """
    if file is None:
        raise ValueError("No audio file provided")

    # Read into memory (safer for async upload file objects that may close).
    try:
        data = file.read()
    except Exception as e:
        raise RuntimeError(f"Failed to read uploaded audio: {e}") from e

    if not data:
        raise ValueError("Uploaded audio file is empty")

    try:
        audio_buffer = io.BytesIO(data)
        model = _get_model()

        segments, info = model.transcribe(
            audio_buffer,
            language=(language or "en"),
            beam_size=5,
            vad_filter=True,
        )

        text_parts = []
        for seg in segments:
            t = (seg.text or "").strip()
            if t:
                text_parts.append(t)

        return " ".join(text_parts).strip()
    except Exception as e:
        logger.exception("Speech transcription failed")
        raise RuntimeError(
            "Speech-to-text failed. Ensure the uploaded audio is a supported format "
            "and that Faster-Whisper model downloads (if needed) succeed."
        ) from e

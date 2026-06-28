from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path


class AudioProcessingError(ValueError):
    pass


@dataclass
class AudioMetadata:
    extension: str | None
    codec: str | None
    sample_rate_hz: int | None
    channels: int | None
    bit_depth: int | None
    duration_ms: int | None
    size_bytes: int
    format_name: str | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PreparedAudio:
    path: str
    original: AudioMetadata
    azure_input: AudioMetadata
    normalized: bool
    warnings: list[str]
    temporary_paths: list[str]

    def cleanup(self) -> None:
        for path in self.temporary_paths:
            for attempt in range(10):
                try:
                    Path(path).unlink(missing_ok=True)
                    break
                except PermissionError:
                    if attempt == 9:
                        break
                    time.sleep(0.05)


class AssessmentAudioProcessor:
    def prepare(
        self,
        audio_content: bytes,
        audio_format: str | None = None,
    ) -> PreparedAudio:
        return prepare_audio(audio_content, audio_format)


_FORMAT_SUFFIXES = {
    "audio/wav": ".wav",
    "audio/wave": ".wav",
    "audio/x-wav": ".wav",
    "wav": ".wav",
    "audio/mpeg": ".mp3",
    "audio/mp3": ".mp3",
    "mp3": ".mp3",
    "audio/mp4": ".m4a",
    "m4a": ".m4a",
    "audio/webm": ".webm",
    "webm": ".webm",
    "audio/ogg": ".ogg",
    "ogg": ".ogg",
}


def _suffix(audio_content: bytes, audio_format: str | None) -> str:
    if audio_format:
        normalized = audio_format.lower().split(";", 1)[0].strip().lstrip(".")
        if normalized in _FORMAT_SUFFIXES:
            return _FORMAT_SUFFIXES[normalized]
    if audio_content[:4] == b"RIFF" and audio_content[8:12] == b"WAVE":
        return ".wav"
    if audio_content[:3] == b"ID3" or audio_content[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}:
        return ".mp3"
    raise AudioProcessingError("Unsupported or unrecognized audio format")


def _inspect_wav(path: str) -> AudioMetadata:
    try:
        with wave.open(path, "rb") as source:
            channels = source.getnchannels()
            sample_rate = source.getframerate()
            sample_width = source.getsampwidth()
            frames = source.getnframes()
            compression = source.getcomptype()
    except (wave.Error, EOFError, OSError) as exc:
        raise AudioProcessingError(f"Corrupt WAV audio: {exc}") from exc
    if compression != "NONE":
        raise AudioProcessingError(f"Unsupported WAV codec: {compression}")
    return AudioMetadata(
        extension=".wav",
        codec=f"pcm_s{sample_width * 8}le",
        sample_rate_hz=sample_rate,
        channels=channels,
        bit_depth=sample_width * 8,
        duration_ms=round(frames / sample_rate * 1000) if sample_rate else None,
        size_bytes=Path(path).stat().st_size,
        format_name="wav",
    )


def _inspect_with_ffprobe(path: str, suffix: str) -> AudioMetadata:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return AudioMetadata(
            extension=suffix,
            codec=None,
            sample_rate_hz=None,
            channels=None,
            bit_depth=None,
            duration_ms=None,
            size_bytes=Path(path).stat().st_size,
            format_name=suffix.lstrip("."),
        )
    process = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=format_name,duration,size:stream=codec_name,sample_rate,channels,bits_per_sample",
            "-of",
            "json",
            path,
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if process.returncode:
        raise AudioProcessingError(f"Corrupt audio: {process.stderr.strip() or 'ffprobe failed'}")
    try:
        payload = json.loads(process.stdout)
        stream = payload["streams"][0]
        media_format = payload.get("format", {})
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise AudioProcessingError("Corrupt audio: no readable audio stream") from exc
    duration = media_format.get("duration")
    return AudioMetadata(
        extension=suffix,
        codec=stream.get("codec_name"),
        sample_rate_hz=_safe_int(stream.get("sample_rate")),
        channels=_safe_int(stream.get("channels")),
        bit_depth=_safe_int(stream.get("bits_per_sample")) or None,
        duration_ms=round(float(duration) * 1000) if duration is not None else None,
        size_bytes=_safe_int(media_format.get("size")) or Path(path).stat().st_size,
        format_name=media_format.get("format_name"),
    )


def _safe_int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def prepare_audio(audio_content: bytes, audio_format: str | None = None) -> PreparedAudio:
    if not audio_content:
        raise AudioProcessingError("Empty audio file")
    suffix = _suffix(audio_content, audio_format)
    input_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temporary_paths = [input_file.name]
    try:
        input_file.write(audio_content)
        input_file.close()
        original = (
            _inspect_wav(input_file.name)
            if suffix == ".wav"
            else _inspect_with_ffprobe(input_file.name, suffix)
        )
        compliant = (
            original.codec == "pcm_s16le"
            and original.sample_rate_hz == 16000
            and original.channels == 1
            and original.bit_depth == 16
        )
        if compliant:
            return PreparedAudio(
                path=input_file.name,
                original=original,
                azure_input=original,
                normalized=False,
                warnings=[],
                temporary_paths=temporary_paths,
            )

        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise AudioProcessingError(
                "Audio must be PCM signed 16-bit little-endian, mono, 16000 Hz; "
                "FFmpeg is required to normalize this file but is not installed"
            )
        output_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        output_file.close()
        temporary_paths.append(output_file.name)
        process = subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-i",
                input_file.name,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                output_file.name,
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if process.returncode:
            raise AudioProcessingError(
                f"Audio normalization failed: {process.stderr.strip() or 'FFmpeg failed'}"
            )
        azure_input = _inspect_wav(output_file.name)
        return PreparedAudio(
            path=output_file.name,
            original=original,
            azure_input=azure_input,
            normalized=True,
            warnings=["Audio was normalized to PCM 16-bit, mono, 16000 Hz for Azure Speech"],
            temporary_paths=temporary_paths,
        )
    except Exception:
        input_file.close()
        for path in temporary_paths:
            Path(path).unlink(missing_ok=True)
        raise

from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.assessment.application.exceptions_speech_to_text import (
    WhisperInferenceError,
    WhisperModelLoadError,
)
from app.assessment.application.ports.speech_service import SpeechAssessmentResult
from app.assessment.application.ports.speech_to_text import (
    TranscriptionResult,
    TranscriptionSegment,
    TranscriptionWord,
)
from app.assessment.application.use_cases.assess_reading_pipeline import (
    AssessReadingCommand,
    AssessReadingPipelineUseCase,
)
from app.assessment.domain.assessment_review import determine_manual_review
from app.assessment.infrastructure.adapters.faster_whisper_stt import (
    FasterWhisperModelProvider,
    FasterWhisperSpeechToTextAdapter,
    WhisperConfig,
)


def _word(text: str, start: float, end: float, probability: float = 0.9):
    return SimpleNamespace(word=text, start=start, end=end, probability=probability)


def _segment(
    text: str = "La perra está en casa.",
    *,
    start: float = 0.1,
    end: float = 2.8,
    avg_logprob: float = -0.2,
    no_speech_prob: float = 0.01,
    words=None,
):
    return SimpleNamespace(
        text=text,
        start=start,
        end=end,
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        words=words or [],
    )


def _info(duration: float = 3.0):
    return SimpleNamespace(language="es", language_probability=0.98, duration=duration)


def _adapter(model: MagicMock, config: WhisperConfig | None = None):
    FasterWhisperModelProvider.clear_cache()
    provider = FasterWhisperModelProvider(model_factory=lambda *args, **kwargs: model)
    return FasterWhisperSpeechToTextAdapter(config or WhisperConfig(), provider)


def test_whisper_returns_text_segments_words_and_real_metrics():
    model = MagicMock()
    model.transcribe.return_value = (
        iter(
            [
                _segment(
                    words=[
                        _word("La", 0.1, 0.3),
                        _word("perra", 0.3, 0.8, 0.85),
                    ]
                )
            ]
        ),
        _info(),
    )
    result = asyncio.run(_adapter(model).transcribe("normalized.wav"))
    assert result.text == "La perra está en casa."
    assert result.language_probability == 0.98
    assert result.segments[0].words[1].text == "perra"
    assert result.segments[0].words[1].probability == 0.85
    assert result.confidence_heuristic is None
    assert result.real_time_factor is not None
    model.transcribe.assert_called_once_with(
        "normalized.wav",
        language="es",
        beam_size=5,
        word_timestamps=True,
        vad_filter=False,
        condition_on_previous_text=False,
    )


def test_whisper_combines_multiple_segments_without_reference_prompt():
    model = MagicMock()
    model.transcribe.return_value = (
        iter([_segment("La perra"), _segment("está en casa")]),
        _info(),
    )
    result = asyncio.run(_adapter(model).transcribe("audio.wav"))
    assert result.text == "La perra está en casa"
    kwargs = model.transcribe.call_args.kwargs
    assert "initial_prompt" not in kwargs
    assert "hotwords" not in kwargs


def test_whisper_empty_and_no_speech_are_reported():
    model = MagicMock()
    model.transcribe.return_value = (
        iter([_segment("", no_speech_prob=0.91)]),
        _info(),
    )
    result = asyncio.run(_adapter(model).transcribe("audio.wav"))
    assert result.text == ""
    assert "EMPTY_TRANSCRIPTION" in result.warnings
    assert "HIGH_NO_SPEECH_PROBABILITY" in result.warnings


def test_whisper_model_load_failure_is_specific():
    FasterWhisperModelProvider.clear_cache()
    provider = FasterWhisperModelProvider(
        model_factory=lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("download unavailable")
        )
    )
    adapter = FasterWhisperSpeechToTextAdapter(WhisperConfig(), provider)
    with pytest.raises(WhisperModelLoadError):
        asyncio.run(adapter.transcribe("audio.wav"))


def test_whisper_inference_failure_is_specific():
    model = MagicMock()
    model.transcribe.side_effect = RuntimeError("decoder failed")
    with pytest.raises(WhisperInferenceError):
        asyncio.run(_adapter(model).transcribe("audio.wav"))


def test_cpu_and_cuda_configuration_are_not_hardcoded():
    cpu = WhisperConfig(device="cpu", compute_type="int8")
    cuda = WhisperConfig(device="cuda", compute_type="float16")
    assert (cpu.device, cpu.compute_type) == ("cpu", "int8")
    assert (cuda.device, cuda.compute_type) == ("cuda", "float16")


def test_configuration_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "base")
    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "float16")
    monkeypatch.setenv("WHISPER_BEAM_SIZE", "3")
    monkeypatch.setenv("WHISPER_VAD_FILTER", "true")
    config = WhisperConfig.from_environment()
    assert config.model_size == "base"
    assert config.device == "cuda"
    assert config.compute_type == "float16"
    assert config.beam_size == 3
    assert config.vad_filter is True


def test_model_is_loaded_once_per_worker_configuration():
    FasterWhisperModelProvider.clear_cache()
    calls = []
    model = MagicMock()

    def factory(*args, **kwargs):
        calls.append((args, kwargs))
        return model

    provider = FasterWhisperModelProvider(model_factory=factory)
    first, first_load_ms = provider.get_model(WhisperConfig(model_size="tiny"))
    second, second_load_ms = provider.get_model(WhisperConfig(model_size="tiny"))
    assert first is second
    assert len(calls) == 1
    assert first_load_ms is not None
    assert second_load_ms is None


def test_repeated_transcriptions_do_not_reload_model():
    FasterWhisperModelProvider.clear_cache()
    loads = []
    model = MagicMock()
    model.transcribe.side_effect = [
        (iter([_segment()]), _info()),
        (iter([_segment()]), _info()),
    ]

    def factory(*args, **kwargs):
        loads.append(1)
        return model

    adapter = FasterWhisperSpeechToTextAdapter(
        WhisperConfig(model_size="tiny"),
        FasterWhisperModelProvider(model_factory=factory),
    )

    async def twice():
        await adapter.transcribe("first.wav")
        await adapter.transcribe("second.wav")

    asyncio.run(twice())
    assert len(loads) == 1
    assert model.transcribe.call_count == 2


class _Metadata:
    duration_ms = 3324
    sample_rate_hz = 16000
    channels = 1
    bit_depth = 16

    def to_dict(self):
        return {
            "duration_ms": self.duration_ms,
            "sample_rate_hz": self.sample_rate_hz,
            "channels": self.channels,
            "bit_depth": self.bit_depth,
        }


class _Prepared:
    path = "one-normalized-file.wav"
    original = _Metadata()
    azure_input = _Metadata()
    normalized = True
    warnings = []

    def __init__(self):
        self.cleaned = False

    def cleanup(self):
        self.cleaned = True


class _AudioProcessor:
    def __init__(self):
        self.calls = 0
        self.prepared = _Prepared()

    def prepare(self, audio_content, audio_format=None):
        self.calls += 1
        return self.prepared


def _transcription(text: str = "La perra está en casa") -> TranscriptionResult:
    return TranscriptionResult(
        text=text,
        language="es",
        language_probability=0.98,
        duration_seconds=3.2,
        segments=[
            TranscriptionSegment(
                text=text,
                start_seconds=0.1,
                end_seconds=3.1,
                avg_logprob=-0.2,
                no_speech_prob=0.01,
                words=[
                    TranscriptionWord("La", 0.1, 0.3, 0.9),
                    TranscriptionWord("perra", 0.3, 0.8, 0.9),
                ],
            )
        ],
        provider="faster_whisper",
        model="small",
    )


class _STT:
    def __init__(self, value=None, error=None):
        self.value = value or _transcription()
        self.error = error
        self.paths = []

    async def transcribe(self, audio_path, language="es"):
        self.paths.append(audio_path)
        await asyncio.sleep(0)
        if self.error:
            raise self.error
        return self.value


class _Azure:
    def __init__(self, value=None, error=None):
        self.value = value or SpeechAssessmentResult(
            status="completed",
            expected_text="El gato está en casa",
            recognized_text="El gato está está en casa.",
            assessment_display_text="El gato está está en casa.",
            assessment_lexical_text="el gato está está en casa",
            language_code="es-MX",
            accuracy_score=85,
            fluency_score=59,
            completeness_score=80,
            pronunciation_score=68.4,
            diagnostics={"session_id": "session"},
        )
        self.error = error
        self.paths = []
        self.references = []

    def assess_normalized_audio(self, prepared, reference_text, language_code=None):
        self.paths.append(prepared.path)
        self.references.append(reference_text)
        if self.error:
            raise self.error
        return self.value


def _run_pipeline(stt=None, azure=None):
    processor = _AudioProcessor()
    stt = stt or _STT()
    azure = azure or _Azure()
    use_case = AssessReadingPipelineUseCase(processor, stt, azure)
    response = asyncio.run(
        use_case.execute(
            AssessReadingCommand(
                audio_content=b"audio",
                expected_text="El gato está en casa",
                audio_format="audio/wav",
                assessment_locale="es-MX",
            )
        )
    )
    return response, processor, stt, azure


def test_pipeline_normalizes_once_and_runs_independent_providers():
    response, processor, stt, azure = _run_pipeline()
    assert processor.calls == 1
    assert stt.paths == ["one-normalized-file.wav"]
    assert azure.paths == ["one-normalized-file.wav"]
    assert azure.references == ["El gato está en casa"]
    assert processor.prepared.cleaned is True
    assert response["status"] == "completed"


def test_pipeline_runs_providers_concurrently():
    class SlowSTT(_STT):
        async def transcribe(self, audio_path, language="es"):
            await asyncio.sleep(0.15)
            return self.value

    class SlowAzure(_Azure):
        def assess_normalized_audio(self, prepared, reference_text, language_code=None):
            time.sleep(0.15)
            return self.value

    started = time.perf_counter()
    _run_pipeline(stt=SlowSTT(), azure=SlowAzure())
    elapsed = time.perf_counter() - started
    assert elapsed < 0.27


def test_pipeline_comparison_uses_whisper_and_not_azure():
    response, *_ = _run_pipeline()
    comparison = response["comparison"]
    assert response["recognized_text"] == "La perra está en casa"
    assert response["assessment_recognized_text"] == "El gato está está en casa."
    assert comparison["source"] == "expected_text_vs_faster_whisper"
    assert comparison["matches"] == 3
    assert comparison["substitutions"] == 2
    assert comparison["omissions"] == 0
    assert comparison["insertions"] == 0
    assert comparison["lexical_match_percentage"] == 60.0
    assert comparison["wer"] == 0.4
    assert comparison["wer_percentage"] == 40.0


def test_pipeline_returns_partial_if_azure_fails_without_inventing_scores():
    response, *_ = _run_pipeline(azure=_Azure(error=TimeoutError()))
    assert response["status"] == "partial"
    assert response["stt_status"] == "completed"
    assert response["pronunciation_status"] == "failed"
    assert response["pronunciation_score"] is None
    assert response["review"]["required"] is True
    assert "PRONUNCIATION_PROVIDER_FAILED" in response["review"]["reasons"]


def test_pipeline_returns_partial_if_whisper_fails_without_azure_fallback():
    response, *_ = _run_pipeline(stt=_STT(error=WhisperInferenceError()))
    assert response["status"] == "partial"
    assert response["recognized_text"] is None
    assert response["assessment_recognized_text"] is not None
    assert response["comparison"] is None
    assert response["stt"]["error"]["code"] == "WHISPER_INFERENCE_ERROR"


def test_empty_whisper_result_is_partial_and_never_replaced_by_azure():
    response, *_ = _run_pipeline(stt=_STT(value=_transcription("")))
    assert response["status"] == "partial"
    assert response["stt_status"] == "empty"
    assert response["recognized_text"] == ""
    assert "EMPTY_ASR_TRANSCRIPTION" in response["review"]["reasons"]


def test_manual_review_rules_cover_quality_timestamps_repetition_and_unicode():
    transcription = TranscriptionResult(
        text="niño niño niño",
        language="es",
        language_probability=0.9,
        duration_seconds=0.3,
        segments=[
            TranscriptionSegment(
                text="niño niño niño",
                start_seconds=0,
                end_seconds=2,
                avg_logprob=-2,
                no_speech_prob=0.8,
                words=[TranscriptionWord("niño", 0.4, 0.2, 0.2)],
            )
        ],
        provider="faster_whisper",
        model="small",
    )
    review = determine_manual_review(
        transcription,
        azure_text="otra frase",
        audio_duration_seconds=0.3,
        low_logprob_threshold=-1.0,
    )
    assert review["required"] is True
    assert {
        "HIGH_NO_SPEECH_PROBABILITY",
        "LOW_ASR_QUALITY",
        "LOW_WORD_PROBABILITY",
        "AUDIO_TOO_SHORT",
        "INVALID_WORD_TIMESTAMPS",
        "ASR_REPETITION",
        "ASR_AZURE_TRANSCRIPT_DIVERGENCE",
    }.issubset(review["reasons"])


def test_result_serializes_missing_metrics_as_null():
    result = _transcription()
    payload = result.to_dict()
    assert payload["confidence_heuristic"] is None
    assert payload["model_load_time_ms"] is None

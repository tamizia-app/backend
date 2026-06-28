from __future__ import annotations

import asyncio
import gc
import time
from dataclasses import dataclass
from typing import Protocol

from app.assessment.application.exceptions_speech_to_text import SpeechToTextError
from app.assessment.application.ports.audio_processing import (
    AudioPreparationPort,
    PreparedAudioPort,
)
from app.assessment.application.ports.speech_service import SpeechAssessmentResult
from app.assessment.application.ports.speech_to_text import (
    SpeechToTextPort,
    TranscriptionResult,
)
from app.assessment.domain.assessment_review import determine_manual_review
from app.assessment.domain.text_comparison import compare_texts


class NormalizedPronunciationAssessmentPort(Protocol):
    def assess_normalized_audio(
        self,
        prepared_audio: PreparedAudioPort,
        reference_text: str,
        language_code: str | None = None,
    ) -> SpeechAssessmentResult: ...


@dataclass(frozen=True)
class AssessReadingCommand:
    audio_content: bytes
    expected_text: str
    audio_format: str | None = None
    assessment_locale: str | None = None
    skip_azure: bool = False


class AssessReadingPipelineUseCase:
    def __init__(
        self,
        audio_processor: AudioPreparationPort,
        stt_service: SpeechToTextPort,
        pronunciation_service: NormalizedPronunciationAssessmentPort,
        *,
        low_logprob_threshold: float = -1.0,
    ) -> None:
        self._audio_processor = audio_processor
        self._stt_service = stt_service
        self._pronunciation_service = pronunciation_service
        self._low_logprob_threshold = low_logprob_threshold

    async def execute(self, command: AssessReadingCommand) -> dict:
        started = time.perf_counter()
        prepared = self._audio_processor.prepare(
            command.audio_content,
            command.audio_format,
        )
        try:
            stt_task = self._timed_stt(prepared.path)
            if command.skip_azure:
                stt_outcome = await stt_task
                pronunciation_outcome: tuple[SpeechAssessmentResult | Exception, int] = (
                    RuntimeError("Azure skipped"),
                    0,
                )
            else:
                stt_outcome, pronunciation_outcome = await asyncio.gather(
                    stt_task,
                    self._timed_pronunciation(
                        prepared,
                        command.expected_text,
                        command.assessment_locale,
                    ),
                )
            return self._build_response(
                command,
                prepared,
                stt_outcome,
                pronunciation_outcome,
                round((time.perf_counter() - started) * 1000),
            )
        finally:
            gc.collect()
            prepared.cleanup()

    async def _timed_stt(
        self,
        audio_path: str,
    ) -> tuple[TranscriptionResult | Exception, int]:
        started = time.perf_counter()
        try:
            result: TranscriptionResult | Exception = await self._stt_service.transcribe(
                audio_path,
                language="es",
            )
        except Exception as exc:
            result = exc
        return result, round((time.perf_counter() - started) * 1000)

    async def _timed_pronunciation(
        self,
        prepared: PreparedAudioPort,
        expected_text: str,
        locale: str | None,
    ) -> tuple[SpeechAssessmentResult | Exception, int]:
        started = time.perf_counter()
        try:
            result: SpeechAssessmentResult | Exception = await asyncio.to_thread(
                self._pronunciation_service.assess_normalized_audio,
                prepared,
                expected_text,
                locale,
            )
        except Exception as exc:
            result = exc
        return result, round((time.perf_counter() - started) * 1000)

    def _build_response(
        self,
        command: AssessReadingCommand,
        prepared: PreparedAudioPort,
        stt_outcome: tuple[TranscriptionResult | Exception, int],
        pronunciation_outcome: tuple[SpeechAssessmentResult | Exception, int],
        total_time_ms: int,
    ) -> dict:
        stt_value, stt_time_ms = stt_outcome
        pronunciation_value, pronunciation_time_ms = pronunciation_outcome
        transcription = stt_value if isinstance(stt_value, TranscriptionResult) else None
        assessment = (
            pronunciation_value
            if isinstance(pronunciation_value, SpeechAssessmentResult)
            else None
        )
        stt_failed = transcription is None
        stt_unusable = transcription is None or not transcription.text.strip()
        azure_skipped = command.skip_azure
        azure_failed = not azure_skipped and (
            assessment is None or assessment.status != "completed"
        )

        if stt_unusable and azure_failed:
            status = "failed"
        elif stt_unusable or azure_failed:
            status = "partial"
        else:
            status = "completed"

        recognized_text = transcription.text if transcription else None
        comparison = (
            compare_texts(command.expected_text, recognized_text).to_dict()
            if recognized_text is not None
            else None
        )
        if comparison is not None:
            comparison["source"] = "expected_text_vs_faster_whisper"

        azure_text = assessment.recognized_text if assessment else None
        audio_duration_seconds = (
            prepared.azure_input.duration_ms / 1000
            if prepared.azure_input.duration_ms is not None
            else None
        )
        review = determine_manual_review(
            transcription,
            azure_text=azure_text,
            audio_duration_seconds=audio_duration_seconds,
            low_logprob_threshold=self._low_logprob_threshold,
            stt_failed=stt_failed,
            azure_failed=azure_failed,
        )

        warnings = list(prepared.warnings)
        if transcription:
            warnings.extend(transcription.warnings)
        if stt_failed:
            warnings.append(_error_code(stt_value, "STT_PROVIDER_FAILED"))
        if azure_failed:
            warnings.append(_assessment_error_code(assessment, pronunciation_value))
        if azure_skipped:
            warnings.append("AZURE_ASSESSMENT_SKIPPED")

        pronunciation_payload = self._pronunciation_payload(
            assessment,
            pronunciation_value,
            skipped=azure_skipped,
        )
        response = {
            "status": status,
            "stt_status": (
                "failed"
                if stt_failed
                else "empty"
                if stt_unusable
                else "completed"
            ),
            "pronunciation_status": (
                "skipped"
                if azure_skipped
                else "failed"
                if azure_failed
                else "completed"
            ),
            "expected_text": command.expected_text,
            "recognized_text": recognized_text,
            "stt_recognized_text": recognized_text,
            "assessment_recognized_text": azure_text,
            "assessment_display_text": (
                assessment.assessment_display_text if assessment else None
            ),
            "assessment_lexical_text": (
                assessment.assessment_lexical_text if assessment else None
            ),
            "stt": (
                {"status": "completed", **transcription.to_dict()}
                if transcription
                else {
                    "status": "failed",
                    "error": _error_payload(stt_value, "STT_PROVIDER_FAILED"),
                }
            ),
            "pronunciation_assessment": pronunciation_payload,
            "comparison": comparison,
            "review": review,
            "diagnostics": {
                "audio_duration_ms": prepared.azure_input.duration_ms,
                "sample_rate_hz": prepared.azure_input.sample_rate_hz,
                "channels": prepared.azure_input.channels,
                "bit_depth": prepared.azure_input.bit_depth,
                "audio_normalized": prepared.normalized,
                "original_audio": prepared.original.to_dict(),
                "normalized_audio": prepared.azure_input.to_dict(),
                "processing_time_ms": total_time_ms,
                "stt_processing_time_ms": stt_time_ms,
                "assessment_processing_time_ms": pronunciation_time_ms,
                "warnings": list(dict.fromkeys(warnings)),
            },
        }
        if assessment:
            response.update(
                pronunciation_score=assessment.pronunciation_score,
                accuracy_score=assessment.accuracy_score,
                fluency_score=assessment.fluency_score,
                completeness_score=assessment.completeness_score,
                prosody_score=assessment.prosody_score,
                locale=assessment.language_code,
                language_code=assessment.language_code,
                duration_ms=assessment.duration_ms,
                raw_result_json=assessment.raw_result_json,
            )
        else:
            response.update(
                pronunciation_score=None,
                accuracy_score=None,
                fluency_score=None,
                completeness_score=None,
                prosody_score=None,
                locale=command.assessment_locale,
                language_code=command.assessment_locale,
                duration_ms=prepared.azure_input.duration_ms,
                raw_result_json={},
            )
        response["missing_fields"] = [
            name
            for name in (
                "pronunciation_score",
                "accuracy_score",
                "fluency_score",
                "completeness_score",
                "prosody_score",
            )
            if response[name] is None
        ]
        response["error_message"] = (
            None if status == "completed" else "One or more assessment providers failed."
        )
        response["error"] = (
            None
            if status == "completed"
            else {"code": "PARTIAL_RESULT" if status == "partial" else "PIPELINE_FAILED"}
        )
        return response

    @staticmethod
    def _pronunciation_payload(
        assessment: SpeechAssessmentResult | None,
        raw_value: SpeechAssessmentResult | Exception,
        *,
        skipped: bool,
    ) -> dict:
        if skipped:
            return {"status": "skipped", "provider": "azure_speech"}
        if assessment is None:
            return {
                "status": "failed",
                "provider": "azure_speech",
                "error": _error_payload(raw_value, "PRONUNCIATION_PROVIDER_FAILED"),
            }
        return {
            "status": assessment.status,
            "provider": "azure_speech",
            "locale": assessment.language_code,
            "recognized_text": assessment.recognized_text,
            "display_text": assessment.assessment_display_text,
            "lexical_text": assessment.assessment_lexical_text,
            "accuracy_score": assessment.accuracy_score,
            "fluency_score": assessment.fluency_score,
            "completeness_score": assessment.completeness_score,
            "pronunciation_score": assessment.pronunciation_score,
            "prosody_score": assessment.prosody_score,
            "prosody_supported": assessment.prosody_supported,
            "words": assessment.words,
            "session_id": assessment.diagnostics.get("session_id"),
            "error": (
                {
                    "code": assessment.error_code,
                    "message": assessment.error_message,
                }
                if assessment.error_message
                else None
            ),
        }


def _error_code(value: object, fallback: str) -> str:
    return value.code if isinstance(value, SpeechToTextError) else fallback


def _error_payload(value: object, fallback: str) -> dict:
    if isinstance(value, SpeechToTextError):
        return {"code": value.code, "message": value.public_message}
    return {"code": fallback, "message": "The provider could not complete the request."}


def _assessment_error_code(
    assessment: SpeechAssessmentResult | None,
    value: object,
) -> str:
    if assessment and assessment.error_code:
        return assessment.error_code
    return "PRONUNCIATION_PROVIDER_FAILED"

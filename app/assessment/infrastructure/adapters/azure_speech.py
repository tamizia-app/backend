from __future__ import annotations

import gc
import json
import logging
import os
import re
from typing import Any

import azure.cognitiveservices.speech as speechsdk
from dotenv import dotenv_values

from app.assessment.application.ports.speech_service import SpeechAssessmentResult
from app.assessment.domain.text_comparison import compare_texts
from app.assessment.infrastructure.audio_processing import (
    AudioProcessingError,
    PreparedAudio,
    prepare_audio,
)
from app.core.config import Settings

logger = logging.getLogger(__name__)

DEFAULT_ASSESSMENT_LOCALE = "es-PE"
ASSESSMENT_LOCALE_ENV = "AZURE_SPEECH_ASSESSMENT_LOCALE"
_LOCALE_PATTERN = re.compile(r"^[a-z]{2,3}(?:-[A-Z]{2})$")
_NUS_SCORE_KEYS = {
    "PronScore": "pronunciation_score",
    "PronunciationScore": "pronunciation_score",
    "AccuracyScore": "accuracy_score",
    "FluencyScore": "fluency_score",
    "CompletenessScore": "completeness_score",
    "ProsodyScore": "prosody_score",
}


def get_assessment_locale(explicit_locale: str | None = None) -> str:
    dotenv_locale = dotenv_values(".env").get(ASSESSMENT_LOCALE_ENV)
    locale = (
        explicit_locale
        or os.getenv(ASSESSMENT_LOCALE_ENV)
        or dotenv_locale
        or DEFAULT_ASSESSMENT_LOCALE
    )
    if not _LOCALE_PATTERN.fullmatch(locale):
        raise ValueError(f"Invalid assessment locale: {locale}")
    return locale


class AzureSpeechPronunciationAssessmentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def assess_pronunciation(
        self,
        audio_content: bytes,
        reference_text: str,
        language_code: str | None = None,
        audio_format: str | None = None,
    ) -> SpeechAssessmentResult:
        try:
            locale = get_assessment_locale(language_code)
        except ValueError as exc:
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                error_code="invalid_locale",
                error_message=str(exc),
            )
        validation_error = self._validate_request(reference_text, locale)
        if validation_error:
            return validation_error

        prepared: PreparedAudio | None = None
        try:
            prepared = prepare_audio(audio_content, audio_format)
            return self._assess_prepared_audio(prepared, reference_text, locale)
        except AudioProcessingError as exc:
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="invalid_audio",
                error_message=str(exc),
            )
        except TimeoutError:
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="timeout",
                error_message="Azure Speech recognition timed out",
            )
        except Exception as exc:
            logger.exception("Azure Speech pronunciation assessment failed")
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="speech_service_error",
                error_message=f"Speech assessment failed: {exc}",
            )
        finally:
            if prepared:
                # Native SDK objects can retain the input handle briefly on Windows.
                gc.collect()
                prepared.cleanup()

    def assess_normalized_audio(
        self,
        prepared_audio: PreparedAudio,
        reference_text: str,
        language_code: str | None = None,
    ) -> SpeechAssessmentResult:
        """Assess a caller-owned normalized file without transcoding or deleting it."""
        try:
            locale = get_assessment_locale(language_code)
        except ValueError as exc:
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                error_code="invalid_locale",
                error_message=str(exc),
            )
        validation_error = self._validate_request(reference_text, locale)
        if validation_error:
            return validation_error
        try:
            return self._assess_prepared_audio(prepared_audio, reference_text, locale)
        except TimeoutError:
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="timeout",
                error_message="Azure Speech recognition timed out",
            )
        except Exception as exc:
            logger.exception("Azure Speech pronunciation assessment failed")
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="speech_service_error",
                error_message=f"Speech assessment failed: {exc}",
            )

    def _assess_prepared_audio(
        self,
        prepared_audio: PreparedAudio,
        reference_text: str,
        locale: str,
    ) -> SpeechAssessmentResult:
        speech_config = self._build_speech_config()
        speech_config.speech_recognition_language = locale
        speech_config.output_format = speechsdk.OutputFormat.Detailed
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
            "10000",
        )
        result, session_id = self._recognize(
            speech_config,
            prepared_audio.path,
            locale,
            reference_text,
        )
        parsed = self._parse_result(
            result,
            locale,
            reference_text=reference_text,
            prepared_audio=prepared_audio,
        )
        if session_id:
            parsed.diagnostics["session_id"] = session_id
        return parsed

    def _validate_request(
        self,
        reference_text: str,
        locale: str,
    ) -> SpeechAssessmentResult | None:
        if not reference_text or not reference_text.strip():
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="empty_reference_text",
                error_message="Expected text must not be empty",
            )
        if not self._settings.azure_speech_key or not self._settings.azure_speech_region:
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=locale,
                error_code="credentials_not_configured",
                error_message="AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be configured",
            )
        return None

    @staticmethod
    def _recognize(
        speech_config: speechsdk.SpeechConfig,
        audio_path: str,
        locale: str,
        reference_text: str,
    ) -> tuple[speechsdk.SpeechRecognitionResult, str | None]:
        audio_config = speechsdk.AudioConfig(filename=audio_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            language=locale,
            audio_config=audio_config,
        )
        pronunciation_config = speechsdk.PronunciationAssessmentConfig(
            reference_text=reference_text,
            grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
            granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
            enable_miscue=True,
        )
        pronunciation_config.apply_to(recognizer)
        session: dict[str, str | None] = {"id": None}
        recognizer.session_started.connect(
            lambda event: session.update(id=getattr(event, "session_id", None))
        )
        result = recognizer.recognize_once_async().get()
        return result, session["id"]

    def _build_speech_config(self) -> speechsdk.SpeechConfig:
        # Pronunciation Assessment is intentionally configured with region, as
        # documented by Azure, instead of an unrelated/custom endpoint.
        return speechsdk.SpeechConfig(
            subscription=self._settings.azure_speech_key,
            region=self._settings.azure_speech_region,
        )

    def _parse_result(
        self,
        result: speechsdk.SpeechRecognitionResult,
        language_code: str,
        *,
        reference_text: str = "",
        prepared_audio: PreparedAudio | None = None,
    ) -> SpeechAssessmentResult:
        diagnostics = self._base_diagnostics(result, prepared_audio)
        if result.reason == speechsdk.ResultReason.NoMatch:
            diagnostics["recognition_reason"] = "NoMatch"
            return SpeechAssessmentResult(
                status="no_match",
                expected_text=reference_text,
                language_code=language_code,
                error_code="no_match",
                error_message="No speech could be recognized",
                diagnostics=diagnostics,
                comparison=compare_texts(reference_text, "").to_dict(),
            )

        if result.reason == speechsdk.ResultReason.Canceled:
            cancellation = self._cancellation_details(result)
            diagnostics.update(cancellation)
            error_code = self._cancellation_error_code(cancellation.get("cancellation_error_code"))
            return SpeechAssessmentResult(
                status="canceled",
                expected_text=reference_text,
                language_code=language_code,
                error_code=error_code,
                error_message=cancellation.get("cancellation_details") or "Recognition canceled",
                diagnostics=diagnostics,
            )

        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            diagnostics["recognition_reason"] = str(result.reason)
            return SpeechAssessmentResult(
                status="error",
                expected_text=reference_text,
                language_code=language_code,
                error_code="recognition_failed",
                error_message=f"Recognition failed: {result.reason}",
                diagnostics=diagnostics,
            )

        raw_json, json_warning = self._read_detailed_json(result)
        warnings = diagnostics["warnings"]
        if json_warning:
            warnings.append(json_warning)

        nbest = raw_json.get("NBest")
        best: dict[str, Any] = nbest[0] if isinstance(nbest, list) and nbest else {}
        if not best:
            warnings.append("Azure detailed response did not contain NBest")

        display_text = _first_text(best.get("Display"), raw_json.get("DisplayText"))
        lexical_text = _first_text(best.get("Lexical"))
        # result.text is the primary recognized utterance. A real Azure display
        # field is only a fallback; reference_text is never used as recognition.
        recognized_text = _first_text(getattr(result, "text", None), display_text)
        assessment = best.get("PronunciationAssessment")
        if not isinstance(assessment, dict):
            assessment = {}
            if raw_json:
                warnings.append("Azure response did not contain PronunciationAssessment scores")

        scores = self._extract_scores(assessment, best)
        words = self._extract_words(best.get("Words"), warnings)
        comparison = compare_texts(reference_text, recognized_text or "").to_dict()
        duration_ms = (
            prepared_audio.azure_input.duration_ms
            if prepared_audio
            else _ticks_to_ms(raw_json.get("Duration") or best.get("Duration"))
        )

        return SpeechAssessmentResult(
            status="completed",
            expected_text=reference_text,
            recognized_text=recognized_text,
            assessment_display_text=display_text,
            assessment_lexical_text=lexical_text,
            pronunciation_score=scores["pronunciation_score"],
            accuracy_score=scores["accuracy_score"],
            fluency_score=scores["fluency_score"],
            completeness_score=scores["completeness_score"],
            # Azure documents prosody as en-US only. Never manufacture it for Spanish.
            prosody_score=scores["prosody_score"] if language_code == "en-US" else None,
            prosody_supported=language_code == "en-US",
            words=words,
            comparison=comparison,
            diagnostics=diagnostics,
            raw_result_json=raw_json,
            language_code=language_code,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _read_detailed_json(result: speechsdk.SpeechRecognitionResult) -> tuple[dict, str | None]:
        value = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult)
        if not value:
            return {}, "Azure response did not include detailed JSON"
        try:
            parsed = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}, "Azure detailed JSON could not be parsed"
        if not isinstance(parsed, dict):
            return {}, "Azure detailed JSON was not an object"
        return parsed, None

    @classmethod
    def _extract_scores(cls, assessment: dict, best: dict) -> dict[str, float | None]:
        scores: dict[str, float | None] = {
            "pronunciation_score": None,
            "accuracy_score": None,
            "fluency_score": None,
            "completeness_score": None,
            "prosody_score": None,
        }
        for source in (best, assessment):
            for azure_key, field_name in _NUS_SCORE_KEYS.items():
                if source.get(azure_key) is not None:
                    scores[field_name] = cls._safe_round(source[azure_key])
        return scores

    @classmethod
    def _extract_words(cls, value: object, warnings: list[str]) -> list[dict]:
        if not isinstance(value, list):
            warnings.append("Azure detailed response did not contain word results")
            return []
        words: list[dict] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            word_assessment = item.get("PronunciationAssessment")
            word_assessment = word_assessment if isinstance(word_assessment, dict) else {}
            phonemes = []
            for phoneme in item.get("Phonemes") or []:
                if not isinstance(phoneme, dict):
                    continue
                phoneme_assessment = phoneme.get("PronunciationAssessment")
                phoneme_assessment = (
                    phoneme_assessment if isinstance(phoneme_assessment, dict) else {}
                )
                phonemes.append(
                    {
                        "phoneme": phoneme.get("Phoneme"),
                        "accuracy_score": cls._safe_round(
                            phoneme_assessment.get("AccuracyScore")
                        ),
                        "offset": phoneme.get("Offset"),
                        "duration": phoneme.get("Duration"),
                    }
                )
            words.append(
                {
                    "word": item.get("Word"),
                    "accuracy_score": cls._safe_round(word_assessment.get("AccuracyScore")),
                    "error_type": word_assessment.get("ErrorType"),
                    "offset": item.get("Offset"),
                    "duration": item.get("Duration"),
                    "phonemes": phonemes,
                }
            )
        if not words:
            warnings.append("Azure word results were empty")
        return words

    @staticmethod
    def _base_diagnostics(
        result: speechsdk.SpeechRecognitionResult,
        prepared_audio: PreparedAudio | None,
    ) -> dict:
        diagnostics = {
            "recognition_reason": getattr(result.reason, "name", str(result.reason)),
            "session_id": getattr(result, "result_id", None),
            "speech_sdk_version": speechsdk.__version__,
            "audio_duration_ms": None,
            "sample_rate_hz": None,
            "channels": None,
            "bit_depth": None,
            "audio_normalized": False,
            "original_audio": None,
            "azure_audio": None,
            "warnings": [],
        }
        if prepared_audio:
            diagnostics.update(
                audio_duration_ms=prepared_audio.azure_input.duration_ms,
                sample_rate_hz=prepared_audio.azure_input.sample_rate_hz,
                channels=prepared_audio.azure_input.channels,
                bit_depth=prepared_audio.azure_input.bit_depth,
                audio_normalized=prepared_audio.normalized,
                original_audio=prepared_audio.original.to_dict(),
                azure_audio=prepared_audio.azure_input.to_dict(),
                warnings=list(prepared_audio.warnings),
            )
        return diagnostics

    @staticmethod
    def _cancellation_details(result: speechsdk.SpeechRecognitionResult) -> dict[str, str | None]:
        try:
            details = speechsdk.CancellationDetails(result)
            return {
                "cancellation_reason": str(details.reason),
                "cancellation_error_code": str(details.error_code),
                "cancellation_details": details.error_details or None,
            }
        except Exception:
            return {
                "cancellation_reason": "Canceled",
                "cancellation_error_code": None,
                "cancellation_details": "Recognition canceled",
            }

    @staticmethod
    def _cancellation_error_code(value: str | None) -> str:
        lowered = (value or "").lower()
        if "authentication" in lowered or "forbidden" in lowered:
            return "invalid_credentials"
        if "timeout" in lowered:
            return "timeout"
        if "badrequest" in lowered:
            return "invalid_request_or_locale"
        return "azure_canceled"

    @staticmethod
    def _safe_round(value: object) -> float | None:
        if value is None:
            return None
        try:
            return round(float(value), 2)
        except (ValueError, TypeError):
            return None


def _first_text(*values: object) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value
    return None


def _ticks_to_ms(value: object) -> int | None:
    try:
        return round(int(value) / 10_000)
    except (TypeError, ValueError):
        return None

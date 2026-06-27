from __future__ import annotations

import json
import logging
import os
import tempfile
import traceback

import azure.cognitiveservices.speech as speechsdk

from app.assessment.application.ports.speech_service import (
    SpeechAssessmentResult,
    SpeechPronunciationAssessmentService,
)
from app.core.config import Settings

logger = logging.getLogger(__name__)

_NUS_SCORE_KEYS = {
    "PronunciationScore": "pronunciation_score",
    "AccuracyScore": "accuracy_score",
    "FluencyScore": "fluency_score",
    "CompletenessScore": "completeness_score",
    "ProsodyScore": "prosody_score",
}


_SUPPORTED_AUDIO_FORMATS = {"wav", "pcm", "audio/wav", "audio/wave", "audio/x-wav"}


def _validate_audio_format(audio_content: bytes, audio_format: str | None = None) -> None:
    if audio_format and audio_format.lower() not in _SUPPORTED_AUDIO_FORMATS:
        raise ValueError(
            f"Unsupported audio format: {audio_format}. "
            f"Only WAV PCM is supported by the Azure Speech SDK."
        )
    if not (audio_content[:4] == b"RIFF" and audio_content[8:12] == b"WAVE"):
        raise ValueError(
            "Unsupported audio format. Only WAV PCM is supported "
            "by the Azure Speech SDK. Convert your audio to WAV "
            "PCM 16kHz mono 16-bit before uploading."
        )


class AzureSpeechPronunciationAssessmentService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def assess_pronunciation(
        self,
        audio_content: bytes,
        reference_text: str,
        language_code: str = "es-PE",
        audio_format: str | None = None,
    ) -> SpeechAssessmentResult:
        if not self._settings.azure_speech_key:
            return SpeechAssessmentResult(error_message="AZURE_SPEECH_KEY is not configured")

        tmp_path = None
        try:
            _validate_audio_format(audio_content, audio_format)
            speech_config = self._build_speech_config()

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_content)
                tmp_path = tmp.name

            audio_config = speechsdk.AudioConfig(filename=tmp_path)

            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                language=language_code,
                audio_config=audio_config,
            )

            pron_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True,
            )
            pron_config.apply_to(recognizer)

            result = recognizer.recognize_once()

            return self._parse_result(result, language_code)

        except Exception as e:
            logger.error("Azure Speech assessment failed: %s", traceback.format_exc())
            return SpeechAssessmentResult(
                error_message=f"Speech assessment error: {e}",
                language_code=language_code,
            )
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def _build_speech_config(self) -> speechsdk.SpeechConfig:
        if self._settings.azure_speech_endpoint:
            logger.info("Using Azure Speech with endpoint: %s", self._settings.azure_speech_endpoint)
            return speechsdk.SpeechConfig(
                endpoint=self._settings.azure_speech_endpoint,
                subscription=self._settings.azure_speech_key,
            )
        region = self._settings.azure_speech_region or "centralus"
        logger.info("Using Azure Speech with region: %s", region)
        return speechsdk.SpeechConfig(
            subscription=self._settings.azure_speech_key,
            region=region,
        )

    def _parse_result(
        self,
        result: speechsdk.SpeechRecognitionResult,
        language_code: str,
    ) -> SpeechAssessmentResult:
        if result.reason == speechsdk.ResultReason.NoMatch:
            return SpeechAssessmentResult(
                language_code=language_code,
                error_message="No speech could be recognized",
            )

        if result.reason != speechsdk.ResultReason.RecognizedSpeech:
            return SpeechAssessmentResult(
                language_code=language_code,
                error_message=f"Recognition failed: {result.reason}",
            )

        recognized_text = result.text
        raw_json: dict = {}
        scores: dict[str, float | None] = {
            "pronunciation_score": None,
            "accuracy_score": None,
            "fluency_score": None,
            "completeness_score": None,
            "prosody_score": None,
        }
        duration_ms: int | None = None

        json_prop = result.properties.get(
            speechsdk.PropertyId.SpeechServiceResponse_JsonResult
        )
        if json_prop:
            try:
                raw_json = json.loads(json_prop)
            except (json.JSONDecodeError, TypeError):
                pass

        try:
            pron_result = speechsdk.PronunciationAssessmentResult(result)
            scores["pronunciation_score"] = self._safe_round(pron_result.pronunciation_score)
            scores["accuracy_score"] = self._safe_round(pron_result.accuracy_score)
            scores["fluency_score"] = self._safe_round(pron_result.fluency_score)
            scores["completeness_score"] = self._safe_round(pron_result.completeness_score)
        except Exception:
            nus_result = None
            if raw_json.get("NBest"):
                nus_result = raw_json["NBest"][0]
            elif raw_json:
                nus_result = raw_json

            if nus_result:
                for nus_key, our_key in _NUS_SCORE_KEYS.items():
                    val = nus_result.get(nus_key)
                    if val is not None:
                        try:
                            scores[our_key] = round(float(val), 2)
                        except (ValueError, TypeError):
                            pass
                duration_ms = nus_result.get("Duration")

        return SpeechAssessmentResult(
            recognized_text=recognized_text,
            pronunciation_score=scores["pronunciation_score"],
            accuracy_score=scores["accuracy_score"],
            fluency_score=scores["fluency_score"],
            completeness_score=scores["completeness_score"],
            prosody_score=scores["prosody_score"],
            raw_result_json=raw_json,
            language_code=language_code,
            duration_ms=duration_ms,
        )

    @staticmethod
    def _safe_round(value: float | None) -> float | None:
        if value is not None:
            try:
                return round(float(value), 2)
            except (ValueError, TypeError):
                return None
        return None

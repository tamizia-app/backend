from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass

import azure.cognitiveservices.speech as speechsdk

from app.core.config import Settings


@dataclass
class PronunciationServiceResult:
    accuracy_score: float | None
    fluency_score: float | None
    completeness_score: float | None
    pronunciation_score: float | None
    recognized_text: str | None
    raw_response: dict


class PronunciationService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def analyze_audio(self, *, audio_bytes: bytes, reference_text: str, locale: str) -> PronunciationServiceResult:
        if not self.settings.azure_speech_key or not self.settings.azure_speech_region:
            return PronunciationServiceResult(
                accuracy_score=None,
                fluency_score=None,
                completeness_score=None,
                pronunciation_score=None,
                recognized_text=None,
                raw_response={"provider": "mock", "message": "Azure Speech is not configured."},
            )

        speech_config = speechsdk.SpeechConfig(
            subscription=self.settings.azure_speech_key,
            region=self.settings.azure_speech_region,
        )
        speech_config.speech_recognition_language = locale

        with tempfile.NamedTemporaryFile(suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_file.flush()

            audio_config = speechsdk.audio.AudioConfig(filename=temp_file.name)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                language=locale,
                audio_config=audio_config,
            )
            assessment_config = speechsdk.PronunciationAssessmentConfig(
                reference_text=reference_text,
                grading_system=speechsdk.PronunciationAssessmentGradingSystem.HundredMark,
                granularity=speechsdk.PronunciationAssessmentGranularity.Phoneme,
                enable_miscue=True,
            )
            assessment_config.apply_to(recognizer)
            result = recognizer.recognize_once_async().get()

        raw_json = result.properties.get(speechsdk.PropertyId.SpeechServiceResponse_JsonResult, "{}")
        payload = json.loads(raw_json)
        best = payload.get("NBest", [{}])[0]
        pronunciation = best.get("PronunciationAssessment", {})

        return PronunciationServiceResult(
            accuracy_score=pronunciation.get("AccuracyScore"),
            fluency_score=pronunciation.get("FluencyScore"),
            completeness_score=pronunciation.get("CompletenessScore"),
            pronunciation_score=pronunciation.get("PronScore"),
            recognized_text=best.get("Display"),
            raw_response=payload,
        )


from __future__ import annotations

import json
import shutil
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.cognitiveservices.speech import ResultReason

from app.assessment.application.ports.speech_service import SpeechAssessmentResult
from app.assessment.domain.text_comparison import compare_texts
from app.assessment.infrastructure.adapters.azure_speech import (
    AzureSpeechPronunciationAssessmentService,
    get_assessment_locale,
)
from app.assessment.infrastructure.audio_processing import prepare_audio
from app.core.config import Settings
from app.dependencies.auth import get_current_user
from app.main import app


_has_ffmpeg = shutil.which("ffmpeg") is not None


@pytest.mark.parametrize(
    ("expected", "recognized", "counts"),
    [
        ("El gato está en casa", "El gato está en casa", (5, 0, 0, 0)),
        ("El gato", "La gata", (0, 2, 0, 0)),
        ("El gato está", "El gato", (2, 0, 1, 0)),
        ("El gato", "El gran gato", (2, 0, 0, 1)),
        ("uno dos tres", "uno cuatro tres cinco", (2, 1, 0, 1)),
        ("GATO", "gato", (1, 0, 0, 0)),
        ("Hola, mundo.", "hola mundo", (2, 0, 0, 0)),
        ("niño pingüino", "NIÑO PINGÜINO", (2, 0, 0, 0)),
        ("uno uno dos", "uno dos", (2, 0, 1, 0)),
    ],
)
def test_word_alignment_operations(expected, recognized, counts):
    result = compare_texts(expected, recognized)
    assert (
        result.matches,
        result.substitutions,
        result.omissions,
        result.insertions,
    ) == counts


def test_required_cat_dog_case():
    result = compare_texts("El gato está en casa", "La perra está en casa")
    assert result.matches == 3
    assert result.substitutions == 2
    assert result.omissions == 0
    assert result.insertions == 0
    assert result.lexical_match_percentage == 60.0
    assert result.wer == 0.4
    assert result.wer_percentage == 40.0
    assert [item.operation for item in result.alignment] == [
        "substitution",
        "substitution",
        "match",
        "match",
        "match",
    ]


def test_accents_remain_significant():
    result = compare_texts("está", "esta")
    assert result.substitutions == 1
    assert result.matches == 0


def test_empty_expected_text_is_safe():
    result = compare_texts("", "hola")
    assert result.insertions == 1
    assert result.wer is None
    assert result.wer_percentage is None


def test_empty_recognized_text_omits_all_expected_words():
    result = compare_texts("hola mundo", "")
    assert result.omissions == 2
    assert result.wer == 1.0


def _recognized_result(payload: dict, text: str = "La perra está en casa"):
    result = MagicMock(spec=["reason", "text", "properties", "result_id"])
    result.reason = ResultReason.RecognizedSpeech
    result.text = text
    result.result_id = "session-123"
    result.properties.get.return_value = json.dumps(payload)
    return result


def _service():
    return AzureSpeechPronunciationAssessmentService(
        Settings(_env_file=None, azure_speech_key="key", azure_speech_region="eastus")
    )


def test_parser_reads_real_nbest_fields_and_words():
    payload = {
        "DisplayText": "La perra está en casa.",
        "NBest": [
            {
                "Display": "La perra está en casa.",
                "Lexical": "la perra está en casa",
                "PronunciationAssessment": {
                    "AccuracyScore": 82.5,
                    "FluencyScore": 91,
                    "CompletenessScore": 60,
                    "PronScore": 78.4,
                },
                "Words": [
                    {
                        "Word": "la",
                        "Offset": 100,
                        "Duration": 200,
                        "PronunciationAssessment": {
                            "AccuracyScore": 90,
                            "ErrorType": "Insertion",
                        },
                        "Phonemes": [
                            {
                                "Phoneme": "l",
                                "PronunciationAssessment": {"AccuracyScore": 88},
                            }
                        ],
                    }
                ],
            }
        ],
    }
    parsed = _service()._parse_result(
        _recognized_result(payload), "es-MX", reference_text="El gato está en casa"
    )
    assert parsed.status == "completed"
    assert parsed.recognized_text == "La perra está en casa"
    assert parsed.assessment_display_text == "La perra está en casa."
    assert parsed.assessment_lexical_text == "la perra está en casa"
    assert parsed.pronunciation_score == 78.4
    assert parsed.words[0]["error_type"] == "Insertion"
    assert parsed.comparison["substitutions"] == 2
    assert parsed.prosody_score is None
    assert parsed.prosody_supported is False


def test_parser_does_not_replace_recognized_text_with_reference():
    parsed = _service()._parse_result(
        _recognized_result({"NBest": []}, text=""),
        "es-MX",
        reference_text="texto esperado",
    )
    assert parsed.recognized_text is None
    assert parsed.expected_text == "texto esperado"


def test_parser_without_nbest_adds_diagnostic_warning():
    parsed = _service()._parse_result(
        _recognized_result({"DisplayText": "Hola."}, text="Hola"),
        "es-MX",
        reference_text="Hola",
    )
    assert any("NBest" in warning for warning in parsed.diagnostics["warnings"])
    assert parsed.words == []


def test_parser_missing_scores_returns_nulls():
    parsed = _service()._parse_result(
        _recognized_result({"NBest": [{"Lexical": "hola", "Words": []}]}, text="hola"),
        "es-MX",
        reference_text="hola",
    )
    assert parsed.accuracy_score is None
    assert parsed.pronunciation_score is None


def test_no_match_has_explicit_status_and_comparison():
    result = MagicMock(spec=["reason", "result_id"])
    result.reason = ResultReason.NoMatch
    result.result_id = "id"
    parsed = _service()._parse_result(result, "es-MX", reference_text="hola")
    assert parsed.status == "no_match"
    assert parsed.error_code == "no_match"
    assert parsed.comparison["omissions"] == 1


def test_cancellation_has_explicit_status():
    result = MagicMock(spec=["reason", "result_id"])
    result.reason = ResultReason.Canceled
    result.result_id = "id"
    with patch.object(
        AzureSpeechPronunciationAssessmentService,
        "_cancellation_details",
        return_value={
            "cancellation_reason": "Error",
            "cancellation_error_code": "AuthenticationFailure",
            "cancellation_details": "Authentication failed",
        },
    ):
        parsed = _service()._parse_result(result, "es-MX", reference_text="hola")
    assert parsed.status == "canceled"
    assert parsed.error_code == "invalid_credentials"


def test_locale_defaults_to_es_pe(monkeypatch):
    monkeypatch.delenv("AZURE_SPEECH_ASSESSMENT_LOCALE", raising=False)
    assert get_assessment_locale() == "es-PE"
    monkeypatch.setenv("AZURE_SPEECH_ASSESSMENT_LOCALE", "es-ES")
    assert get_assessment_locale() == "es-ES"
    assert get_assessment_locale("es-MX") == "es-MX"


def test_empty_reference_is_rejected_before_azure():
    result = _service().assess_pronunciation(b"audio", " ")
    assert result.error_code == "empty_reference_text"


@pytest.mark.skipif(not _has_ffmpeg, reason="ffmpeg not installed — required to normalize stereo audio")
def test_audio_inspection_for_compliant_and_stereo_files():
    for filename, normalized in (("audios/elgato.wav", False), ("audios/laperra.wav", True)):
        content = open(filename, "rb").read()
        prepared = prepare_audio(content, "audio/wav")
        try:
            assert prepared.normalized is normalized
            assert prepared.azure_input.sample_rate_hz == 16000
            assert prepared.azure_input.channels == 1
            assert prepared.azure_input.bit_depth == 16
        finally:
            prepared.cleanup()


def test_assessment_endpoint_returns_structured_result(client):
    mocked = {
        "status": "completed",
        "stt_status": "completed",
        "pronunciation_status": "completed",
        "expected_text": "El gato",
        "recognized_text": "La perra",
        "stt_recognized_text": "La perra",
        "assessment_recognized_text": "El gato",
        "assessment_display_text": "El gato.",
        "assessment_lexical_text": "el gato",
        "stt": {"provider": "faster_whisper", "text": "La perra"},
        "locale": "es-MX",
        "pronunciation_assessment": {"provider": "azure_speech"},
        "comparison": compare_texts("El gato", "La perra").to_dict(),
        "review": {"required": False, "reasons": []},
        "diagnostics": {"warnings": []},
        "error": None,
        "language_code": "es-MX",
        "duration_ms": 1000,
        "error_message": None,
        "pronunciation_score": 80.0,
        "accuracy_score": 80.0,
        "fluency_score": 80.0,
        "completeness_score": 80.0,
        "prosody_score": None,
        "missing_fields": ["prosody_score"],
        "raw_result_json": {},
    }
    with patch(
        "app.assessment.presentation.routes.AssessReadingPipelineUseCase"
    ) as use_case_class:
        app.dependency_overrides[get_current_user] = lambda: MagicMock(id=uuid.uuid4())
        use_case_class.return_value.execute = AsyncMock(return_value=mocked)
        response = client.post(
            "/api/v1/assessments/dev/speech/pronunciation-assessment",
            files={"file": ("audio.wav", b"not-empty", "audio/wav")},
            data={"reference_text": "El gato", "language_code": "es-MX"},
        )
        app.dependency_overrides.pop(get_current_user, None)
    assert response.status_code == 200
    payload = response.json()
    assert payload["expected_text"] == "El gato"
    assert payload["recognized_text"] == "La perra"
    assert payload["comparison"]["substitutions"] == 2

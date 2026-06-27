from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from azure.cognitiveservices.speech import ResultReason

import uuid
from unittest.mock import patch

from app.assessment.application.ports.speech_service import SpeechAssessmentResult
from app.assessment.infrastructure.adapters.azure_speech import (
    AzureSpeechPronunciationAssessmentService,
    _NUS_SCORE_KEYS,
)
from app.core.config import Settings
from app.dependencies.auth import get_current_user
from app.iam.infrastructure.models.user_model import UserModel
from app.main import app


class TestSpeechServiceConfig:
    def test_config_carga_variables_speech(self):
        settings = Settings(
            _env_file=None,
            azure_speech_key="test-key",
            azure_speech_region="eastus",
            azure_speech_endpoint="https://custom.endpoint.com",
        )
        assert settings.azure_speech_key == "test-key"
        assert settings.azure_speech_region == "eastus"
        assert settings.azure_speech_endpoint == "https://custom.endpoint.com"

    def test_config_valores_default_son_none(self):
        settings = Settings(_env_file=None)
        assert settings.azure_speech_key is None
        assert settings.azure_speech_region is None
        assert settings.azure_speech_endpoint is None


class TestSpeechServicePort:
    def test_result_soporta_campos_faltantes(self):
        result = SpeechAssessmentResult(
            recognized_text="test",
            language_code="es-PE",
        )
        assert result.pronunciation_score is None
        assert result.accuracy_score is None
        assert result.fluency_score is None
        assert result.completeness_score is None
        assert result.prosody_score is None
        assert result.raw_result_json == {}
        assert result.error_message is None

    def test_result_no_falla_con_campos_vacios(self):
        result = SpeechAssessmentResult(language_code="es-PE")
        assert result.pronunciation_score is None
        assert result.recognized_text is None
        assert result.raw_result_json == {}
        assert result.error_message is None

    def test_result_conserva_raw_result_json(self):
        raw = {"NBest": [{"PronunciationScore": 75.0, "AccuracyScore": 80.0}]}
        result = SpeechAssessmentResult(
            recognized_text="hello",
            pronunciation_score=75.0,
            accuracy_score=80.0,
            raw_result_json=raw,
            language_code="en-US",
        )
        assert result.raw_result_json == raw
        assert result.raw_result_json["NBest"][0]["PronunciationScore"] == 75.0


class TestSpeechAdapterParser:
    def test_parser_soporta_campos_faltantes(self):
        """_parse_result no falla cuando el JSON no tiene todos los scores."""
        service = AzureSpeechPronunciationAssessmentService(
            Settings(_env_file=None, azure_speech_key="k", azure_speech_region="r")
        )
        mock_result = MagicMock(spec=["reason", "text", "properties", "json"])
        mock_result.reason = ResultReason.RecognizedSpeech
        mock_result.text = "hola mundo"

        nus_json = json.dumps({"DisplayText": "hola mundo", "NBest": [{"PronunciationScore": 85.0}]})
        mock_result.properties.get.return_value = nus_json

        result = service._parse_result(mock_result, "es-PE")
        assert result.pronunciation_score == 85.0
        assert result.accuracy_score is None
        assert result.fluency_score is None
        assert result.completeness_score is None
        assert result.prosody_score is None
        assert result.recognized_text == "hola mundo"

    def test_parser_no_falla_si_prosody_score_no_existe(self):
        """El parser tolera la ausencia de prosody_score."""
        service = AzureSpeechPronunciationAssessmentService(
            Settings(_env_file=None, azure_speech_key="k", azure_speech_region="r")
        )
        mock_result = MagicMock(spec=["reason", "text", "properties", "json"])
        mock_result.reason = ResultReason.RecognizedSpeech
        mock_result.text = "test"

        nus_json = json.dumps({
            "DisplayText": "test",
            "NBest": [{"PronunciationScore": 90.0, "AccuracyScore": 85.0, "FluencyScore": 80.0}],
        })
        mock_result.properties.get.return_value = nus_json

        result = service._parse_result(mock_result, "es-PE")
        assert result.pronunciation_score == 90.0
        assert result.accuracy_score == 85.0
        assert result.fluency_score == 80.0
        assert result.completeness_score is None
        assert result.prosody_score is None

    def test_parser_conserva_raw_result_json(self):
        """El parser preserva el JSON completo tal cual viene de Azure."""
        service = AzureSpeechPronunciationAssessmentService(
            Settings(_env_file=None, azure_speech_key="k", azure_speech_region="r")
        )
        mock_result = MagicMock(spec=["reason", "text", "properties", "json"])
        mock_result.reason = ResultReason.RecognizedSpeech
        mock_result.text = "raw test"

        raw = {"DisplayText": "raw test", "NBest": [{"PronunciationScore": 75.0}]}
        mock_result.properties.get.return_value = json.dumps(raw)

        result = service._parse_result(mock_result, "en-US")
        assert result.raw_result_json == raw
        assert result.pronunciation_score == 75.0

    def test_parser_maneja_no_match(self):
        """_parse_result retorna error cuando no hay reconocimiento."""
        service = AzureSpeechPronunciationAssessmentService(
            Settings(_env_file=None, azure_speech_key="k", azure_speech_region="r")
        )
        mock_result = MagicMock(spec=["reason", "text", "properties"])
        mock_result.reason = ResultReason.NoMatch

        result = service._parse_result(mock_result, "es-PE")
        assert result.error_message is not None
        assert "No speech" in result.error_message

    def test_parser_maneja_otros_errores(self):
        """_parse_result retorna error genérico para otros ResultReason."""
        service = AzureSpeechPronunciationAssessmentService(
            Settings(_env_file=None, azure_speech_key="k", azure_speech_region="r")
        )
        mock_result = MagicMock(spec=["reason", "text", "properties"])
        mock_result.reason = ResultReason.Canceled

        result = service._parse_result(mock_result, "es-PE")
        assert result.error_message is not None


class TestSpeechEndpointAuth:
    def test_endpoint_requiere_auth(self, client):
        response = client.post("/api/v1/assessments/dev/speech/pronunciation-assessment")
        assert response.status_code == 401

    def test_endpoint_usuario_no_autenticado_devuelve_401(self, client):
        response = client.post(
            "/api/v1/assessments/dev/speech/pronunciation-assessment",
            data={"reference_text": "test"},
        )
        assert response.status_code == 401

    def test_compare_endpoint_requiere_auth(self, client):
        response = client.post("/api/v1/assessments/dev/speech/compare-languages")
        assert response.status_code == 401

    def test_endpoint_bloquea_en_production(self, client):
        mock_user = UserModel(
            id=uuid.uuid4(),
            name="Test",
            lastname="Teacher",
            email="test@test.com",
            password_hash="hash",
            is_active=True,
        )
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("app.assessment.presentation.routes.get_settings") as mock_get_settings:
            settings = Settings(_env_file=None, environment="production")
            settings.azure_speech_key = "test"
            settings.azure_speech_region = "test"
            settings.azure_speech_endpoint = None
            mock_get_settings.return_value = settings

            response = client.post(
                "/api/v1/assessments/dev/speech/pronunciation-assessment",
                files={"file": ("test.wav", b"fake-audio-data", "audio/wav")},
                data={"reference_text": "hello", "language_code": "en-US"},
            )
            assert response.status_code == 403
            assert "production" in response.json()["detail"].lower()

        app.dependency_overrides.pop(get_current_user, None)

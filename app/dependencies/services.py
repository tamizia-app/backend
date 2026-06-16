from fastapi import Depends

from app.core.config import Settings, get_settings
from app.assessment.modules.ai_processing.infrastructure.ocr import OCRService
from app.assessment.modules.ai_processing.infrastructure.speech import PronunciationService
from app.assessment.modules.evidences.infrastructure.storage import ObjectStorageService


def get_storage_service(settings: Settings = Depends(get_settings)) -> ObjectStorageService:
    return ObjectStorageService(settings)


def get_ocr_service(settings: Settings = Depends(get_settings)) -> OCRService:
    return OCRService(settings)


def get_pronunciation_service(settings: Settings = Depends(get_settings)) -> PronunciationService:
    return PronunciationService(settings)

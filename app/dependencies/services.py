from fastapi import Depends

from app.core.config import Settings, get_settings
from app.services.azure.ocr import OCRService
from app.services.azure.speech import PronunciationService
from app.services.azure.storage import ObjectStorageService


def get_storage_service(settings: Settings = Depends(get_settings)) -> ObjectStorageService:
    return ObjectStorageService(settings)


def get_ocr_service(settings: Settings = Depends(get_settings)) -> OCRService:
    return OCRService(settings)


def get_pronunciation_service(settings: Settings = Depends(get_settings)) -> PronunciationService:
    return PronunciationService(settings)

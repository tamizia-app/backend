from __future__ import annotations

import uuid
from pathlib import Path

from azure.storage.blob import BlobServiceClient, ContentSettings

from app.core.config import Settings


class ObjectStorageService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._blob_service_client = (
            BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
            if settings.azure_blob_connection_string
            else None
        )

    def upload_bytes(self, *, content: bytes, folder: str, filename: str, content_type: str) -> str:
        blob_name = f"{folder}/{uuid.uuid4()}-{filename}"
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self.settings.azure_blob_container)
            try:
                container.create_container()
            except Exception:
                pass
            blob_client = container.get_blob_client(blob_name)
            blob_client.upload_blob(content, overwrite=True, content_settings=ContentSettings(content_type=content_type))
            return blob_client.url

        local_root = Path(self.settings.local_storage_path)
        target = local_root / blob_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return str(target.resolve())


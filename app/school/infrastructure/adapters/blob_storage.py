from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from azure.storage.blob import BlobServiceClient, BlobSasPermissions, ContentSettings, generate_blob_sas

from app.core.config import Settings
from app.school.application.exceptions.student_exceptions import BlobStorageError


class AzureConsentBlobStorage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._blob_service_client = (
            BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
            if settings.azure_blob_connection_string
            else None
        )

    def upload_pdf(self, *, content: bytes, teacher_id: UUID, classroom_id: UUID, student_id: UUID, version: int) -> str:
        blob_name = f"{teacher_id}/{classroom_id}/{student_id}/consent_v{version}.pdf"
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self._settings.azure_blob_container)
            try:
                container.create_container()
            except Exception:
                pass
            blob_client = container.get_blob_client(blob_name)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type="application/pdf"),
            )
            return blob_name

        local_root = Path(self._settings.local_storage_path) / "consents"
        target = local_root / blob_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return blob_name

    def download_url(self, *, blob_path: str) -> str:
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self._settings.azure_blob_container)
            blob_client = container.get_blob_client(blob_path)
            sas_token = generate_blob_sas(
                account_name=self._blob_service_client.account_name,
                container_name=self._settings.azure_blob_container,
                blob_name=blob_path,
                account_key=self._blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(UTC) + timedelta(minutes=5),
            )
            return f"{blob_client.url}?{sas_token}"

        local_path = Path(self._settings.local_storage_path) / "consents" / blob_path
        return local_path.as_uri()

    def get_pdf_content(self, *, blob_path: str) -> bytes | None:
        if self._blob_service_client:
            return None
        p = Path(blob_path)
        if p.is_absolute():
            local_path = p
        else:
            local_path = Path(self._settings.local_storage_path) / "consents" / blob_path
        if not local_path.exists():
            return None
        return local_path.read_bytes()

    def get_content(self, *, blob_path: str) -> bytes | None:
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self._settings.azure_blob_container)
            blob_client = container.get_blob_client(blob_path)
            return blob_client.download_blob().readall()
        p = Path(blob_path)
        if p.is_absolute():
            local_path = p
        else:
            local_path = Path(self._settings.local_storage_path) / "consents" / blob_path
        if not local_path.exists():
            return None
        return local_path.read_bytes()

    def template_url(self) -> str:
        return self.download_url(blob_path=f"{self._settings.azure_blob_template_folder}/consent_template.pdf")

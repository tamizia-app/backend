from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas

from app.core.config import Settings


class AzureAssessmentBlobStorage:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._blob_service_client = (
            BlobServiceClient.from_connection_string(settings.azure_blob_connection_string)
            if settings.azure_blob_connection_string
            else None
        )

    def upload_file(
        self,
        *,
        content: bytes,
        content_type: str,
        teacher_id: UUID,
        classroom_id: UUID,
        student_id: UUID,
        assessment_attempt_id: UUID,
        exercise_attempt_id: UUID,
        subfolder: str,
        filename: str,
    ) -> str:
        blob_name = (
            f"{teacher_id}/{classroom_id}/{student_id}/assessments/"
            f"{assessment_attempt_id}/exercise_attempts/{exercise_attempt_id}/"
            f"{subfolder}/{filename}"
        )
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self._settings.azure_storage_assessment_container_name)
            try:
                container.create_container()
            except Exception:
                pass
            blob_client = container.get_blob_client(blob_name)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            return blob_name

        local_root = Path(self._settings.local_storage_path) / "assessments"
        target = local_root / blob_name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return blob_name

    def download_url(self, *, blob_path: str) -> str:
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self._settings.azure_storage_assessment_container_name)
            blob_client = container.get_blob_client(blob_path)
            sas_token = generate_blob_sas(
                account_name=self._blob_service_client.account_name,
                container_name=self._settings.azure_storage_assessment_container_name,
                blob_name=blob_path,
                account_key=self._blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read=True),
                expiry=datetime.now(UTC) + timedelta(minutes=5),
            )
            return f"{blob_client.url}?{sas_token}"

        local_path = Path(self._settings.local_storage_path) / "assessments" / blob_path
        return local_path.as_uri()

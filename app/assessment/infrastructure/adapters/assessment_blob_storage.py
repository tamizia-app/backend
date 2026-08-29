from datetime import UTC, datetime, timedelta
from hashlib import sha256
import os
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

        target = self._local_target(blob_name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return blob_name

    def upload_asset(
        self,
        *,
        content: bytes,
        content_type: str,
        blob_path: str,
    ) -> str:
        if self._blob_service_client:
            container = self._blob_service_client.get_container_client(self._settings.azure_storage_assessment_container_name)
            try:
                container.create_container()
            except Exception:
                pass
            blob_client = container.get_blob_client(blob_path)
            blob_client.upload_blob(
                content,
                overwrite=True,
                content_settings=ContentSettings(content_type=content_type),
            )
            return blob_path

        target = self._local_target(blob_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return blob_path

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

        local_path = self._local_target(blob_path, prefer_existing=True)
        return local_path.as_uri()

    def _local_target(self, blob_path: str, *, prefer_existing: bool = False) -> Path:
        root = Path(self._settings.local_storage_path)
        legacy = root / "assessments" / blob_path
        if prefer_existing and legacy.exists():
            return legacy.resolve()
        # UUID-rich assessment paths can exceed Win32's legacy MAX_PATH. Keep the
        # public blob name stable while mapping only the local fallback to a short,
        # deterministic object path. Azure paths and DB values remain unchanged.
        absolute_length = len(str(legacy.absolute()))
        if os.name != "nt" or absolute_length < 240:
            return legacy.absolute()
        digest = sha256(blob_path.encode("utf-8")).hexdigest()
        suffix = Path(blob_path).suffix[:10]
        return (root / "assessment_objects" / digest[:2] / f"{digest}{suffix}").absolute()

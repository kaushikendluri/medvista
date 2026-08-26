"""Thin REST client for Orthanc, the DICOM server.

Orthanc's own classic REST API (not DICOMweb STOW-RS) is used for upload
and preview rendering because it accepts raw DICOM Part 10 bytes directly
and does the study/series/instance indexing itself — there is no reason
to hand-roll multipart/related DICOMweb framing for a server we control.
WADO-RS (DICOMweb) remains the retrieval path the Phase 3 viewer will use.
"""
import httpx

from app.core.config import get_settings

settings = get_settings()


class OrthancError(Exception):
    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def _client() -> httpx.Client:
    return httpx.Client(
        base_url=settings.DICOM_SERVER_URL,
        auth=(settings.DICOM_SERVER_USERNAME, settings.DICOM_SERVER_PASSWORD),
        timeout=30.0,
    )


def is_available() -> bool:
    try:
        with _client() as client:
            response = client.get("/system")
            return response.status_code == 200
    except httpx.HTTPError:
        return False


def upload_instance(dicom_bytes: bytes) -> dict:
    """Upload one DICOM Part 10 file. Returns Orthanc's response, which
    includes the instance ID, parent series/study IDs, and Status
    ("Success" or "AlreadyStored")."""
    try:
        with _client() as client:
            response = client.post(
                "/instances", content=dicom_bytes, headers={"Content-Type": "application/dicom"}
            )
    except httpx.HTTPError as exc:
        raise OrthancError(f"Unable to reach the DICOM server: {exc}") from None

    if response.status_code not in (200, 202):
        raise OrthancError(
            f"DICOM server rejected the file (HTTP {response.status_code})",
            status_code=response.status_code,
        )
    return response.json()


def fetch_instance_preview(orthanc_instance_id: str) -> tuple[bytes, str]:
    """Rendered preview image for an instance. Returns (bytes, content_type)."""
    try:
        with _client() as client:
            response = client.get(f"/instances/{orthanc_instance_id}/preview")
    except httpx.HTTPError as exc:
        raise OrthancError(f"Unable to reach the DICOM server: {exc}") from None

    if response.status_code == 404:
        raise OrthancError("Instance not found on DICOM server", status_code=404)
    if response.status_code != 200:
        raise OrthancError(
            f"DICOM server error rendering preview (HTTP {response.status_code})",
            status_code=response.status_code,
        )
    return response.content, response.headers.get("content-type", "image/png")

"""DICOM file validation and metadata extraction, via pydicom.

Every value returned here comes from the file's own DICOM header — nothing
is inferred or defaulted to a clinically meaningful value.
"""
import io
from dataclasses import dataclass
from datetime import date

import pydicom
from pydicom.errors import InvalidDicomError

MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024  # 100MB per instance


class InvalidDicomFile(Exception):
    pass


@dataclass
class InstanceMetadata:
    study_uid: str
    series_uid: str
    sop_instance_uid: str
    modality: str
    accession_number: str | None
    study_description: str | None
    series_description: str | None
    study_date: date | None
    institution: str | None
    body_part: str | None
    series_number: int | None
    instance_number: int | None


def _parse_dicom_date(value: str | None) -> date | None:
    if not value or len(value) != 8:
        return None
    try:
        return date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
    except ValueError:
        return None


def extract_metadata(dicom_bytes: bytes, filename: str) -> InstanceMetadata:
    if len(dicom_bytes) > MAX_FILE_SIZE_BYTES:
        raise InvalidDicomFile(f"{filename}: file exceeds the 100MB per-instance limit")

    try:
        dataset = pydicom.dcmread(io.BytesIO(dicom_bytes), stop_before_pixels=True, force=False)
    except InvalidDicomError:
        raise InvalidDicomFile(f"{filename}: not a valid DICOM file") from None
    except Exception as exc:  # pydicom can raise a variety of parse errors
        raise InvalidDicomFile(f"{filename}: could not be parsed ({exc})") from None

    required = ("StudyInstanceUID", "SeriesInstanceUID", "SOPInstanceUID", "Modality")
    missing = [tag for tag in required if tag not in dataset]
    if missing:
        raise InvalidDicomFile(f"{filename}: missing required DICOM tag(s): {', '.join(missing)}")

    def _int_or_none(value) -> int | None:
        try:
            return int(value) if value not in (None, "") else None
        except (ValueError, TypeError):
            return None

    return InstanceMetadata(
        study_uid=str(dataset.StudyInstanceUID),
        series_uid=str(dataset.SeriesInstanceUID),
        sop_instance_uid=str(dataset.SOPInstanceUID),
        modality=str(dataset.Modality),
        accession_number=str(dataset.get("AccessionNumber") or "") or None,
        study_description=str(dataset.get("StudyDescription") or "") or None,
        series_description=str(dataset.get("SeriesDescription") or "") or None,
        study_date=_parse_dicom_date(dataset.get("StudyDate")),
        institution=str(dataset.get("InstitutionName") or "") or None,
        body_part=str(dataset.get("BodyPartExamined") or "") or None,
        series_number=_int_or_none(dataset.get("SeriesNumber")),
        instance_number=_int_or_none(dataset.get("InstanceNumber")),
    )

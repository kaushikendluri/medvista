"""Generates small, fully synthetic DICOM files for tests — no real
patient data, ever. Includes real pixel data so Orthanc's preview
rendering can be exercised end-to-end."""
import io

import numpy as np
import pydicom
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid


def make_synthetic_dicom(
    *,
    study_uid: str | None = None,
    series_uid: str | None = None,
    sop_uid: str | None = None,
    modality: str = "CT",
    study_description: str = "Synthetic Test Study",
    series_description: str = "Synthetic Test Series",
    study_date: str = "20260115",
    body_part: str = "CHEST",
    series_number: int = 1,
    instance_number: int = 1,
    rows: int = 8,
    cols: int = 8,
) -> bytes:
    sop_uid = sop_uid or generate_uid()

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = "1.2.840.10008.5.1.4.1.1.2"  # CT Image Storage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = generate_uid()

    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\x00" * 128)

    ds.PatientName = "Synthetic^Test"
    ds.PatientID = "SYNTH-TEST"
    ds.StudyInstanceUID = study_uid or generate_uid()
    ds.SeriesInstanceUID = series_uid or generate_uid()
    ds.SOPInstanceUID = sop_uid
    ds.SOPClassUID = file_meta.MediaStorageSOPClassUID
    ds.Modality = modality
    ds.StudyDescription = study_description
    ds.SeriesDescription = series_description
    ds.StudyDate = study_date
    ds.BodyPartExamined = body_part
    ds.SeriesNumber = series_number
    ds.InstanceNumber = instance_number
    ds.AccessionNumber = "ACC-TEST-0001"
    ds.InstitutionName = "MedVista Test Institution"

    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    pixels = np.zeros((rows, cols), dtype=np.uint16)
    pixels[:, :] = 500
    ds.PixelData = pixels.tobytes()

    buffer = io.BytesIO()
    pydicom.dcmwrite(buffer, ds, enforce_file_format=True)
    return buffer.getvalue()

# rows that only exist in the disposable test database above; if the real
# ai-worker dequeues one it just no-ops (process_analysis_job returns early
# for an unknown analysis id), so sharing this instance is safe.
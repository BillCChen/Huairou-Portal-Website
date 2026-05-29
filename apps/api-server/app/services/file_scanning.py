from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import FileRecord


SCAN_STATUS_PENDING = "pending"
SCAN_STATUS_CLEAN = "clean"
SCAN_STATUS_INFECTED = "infected"
SCAN_STATUS_FAILED = "failed"
SCAN_STATUS_SKIPPED = "skipped"
SCAN_ENGINE_MOCK = "mock"

SCAN_STATUSES = {
    SCAN_STATUS_PENDING,
    SCAN_STATUS_CLEAN,
    SCAN_STATUS_INFECTED,
    SCAN_STATUS_FAILED,
    SCAN_STATUS_SKIPPED,
}
MOCK_SCAN_READ_LIMIT_BYTES = 1_048_576


@dataclass(frozen=True)
class ScanResult:
    status: str
    engine: str
    message: str
    scanned_at: datetime


def normalize_scan_status(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in SCAN_STATUSES:
        return normalized
    return SCAN_STATUS_PENDING


def get_file_scan_status(file_record: FileRecord | None) -> str | None:
    if not file_record:
        return None
    return normalize_scan_status(file_record.scan_status)


def is_file_download_allowed(file_record: FileRecord | None) -> bool:
    return get_file_scan_status(file_record) == SCAN_STATUS_CLEAN


def scan_file_mock(file_record: FileRecord, resolved_path: Path) -> ScanResult:
    now = datetime.now(UTC)
    name_text = f"{file_record.origin_name or ''} {resolved_path.name}".lower()

    if not resolved_path.is_file():
        return ScanResult(
            status=SCAN_STATUS_FAILED,
            engine=SCAN_ENGINE_MOCK,
            message="File not found during mock scan",
            scanned_at=now,
        )

    try:
        with resolved_path.open("rb") as handle:
            sample = handle.read(MOCK_SCAN_READ_LIMIT_BYTES).lower()
    except OSError:
        return ScanResult(
            status=SCAN_STATUS_FAILED,
            engine=SCAN_ENGINE_MOCK,
            message="Mock scanner could not read file",
            scanned_at=now,
        )

    if "scan-fail" in name_text or b"scan-fail" in sample:
        return ScanResult(
            status=SCAN_STATUS_FAILED,
            engine=SCAN_ENGINE_MOCK,
            message="Mock scanner simulated failure",
            scanned_at=now,
        )

    if "eicar" in name_text or "infected" in name_text or b"eicar" in sample or b"infected" in sample:
        return ScanResult(
            status=SCAN_STATUS_INFECTED,
            engine=SCAN_ENGINE_MOCK,
            message="Mock scanner detected test signature",
            scanned_at=now,
        )

    return ScanResult(
        status=SCAN_STATUS_CLEAN,
        engine=SCAN_ENGINE_MOCK,
        message="Mock scanner passed",
        scanned_at=now,
    )


def mark_file_scan_result(db: Session, file_record: FileRecord, result: ScanResult) -> FileRecord:
    file_record.scan_status = normalize_scan_status(result.status)
    file_record.scan_engine = result.engine[:100]
    file_record.scan_message = result.message[:500]
    file_record.scanned_at = result.scanned_at
    db.flush()
    return file_record

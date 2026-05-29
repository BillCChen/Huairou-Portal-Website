from __future__ import annotations

import socket
import struct
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
SCAN_ENGINE_CLAMD = "clamd"
SCAN_ENGINE_MANUAL_OVERRIDE = "manual_override"

SCAN_STATUSES = {
    SCAN_STATUS_PENDING,
    SCAN_STATUS_CLEAN,
    SCAN_STATUS_INFECTED,
    SCAN_STATUS_FAILED,
    SCAN_STATUS_SKIPPED,
}
SCAN_PROVIDERS = {SCAN_ENGINE_MOCK, SCAN_ENGINE_CLAMD}
MOCK_SCAN_READ_LIMIT_BYTES = 1_048_576
CLAMD_STREAM_CHUNK_SIZE = 65_536
SCAN_MESSAGE_MAX_LENGTH = 1_200


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


def _clean_scan_message(value: str) -> str:
    normalized = " ".join(value.replace("\x00", " ").split())
    return normalized[:SCAN_MESSAGE_MAX_LENGTH] or "Scan completed"


def _read_clamd_response(sock: socket.socket) -> str:
    chunks: list[bytes] = []
    while True:
        data = sock.recv(4096)
        if not data:
            break
        chunks.append(data)
        if b"\0" in data or b"\n" in data:
            break
    return b"".join(chunks).decode("utf-8", errors="replace").strip("\x00\r\n ")


def scan_file_clamd(
    file_record: FileRecord,
    resolved_path: Path,
    *,
    host: str,
    port: int,
    timeout_seconds: float,
) -> ScanResult:
    now = datetime.now(UTC)

    if not resolved_path.is_file():
        return ScanResult(
            status=SCAN_STATUS_FAILED,
            engine=SCAN_ENGINE_CLAMD,
            message="File not found during ClamAV scan",
            scanned_at=now,
        )

    try:
        with socket.create_connection((host, port), timeout=timeout_seconds) as sock:
            sock.settimeout(timeout_seconds)
            sock.sendall(b"zINSTREAM\0")
            with resolved_path.open("rb") as handle:
                while True:
                    chunk = handle.read(CLAMD_STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    sock.sendall(struct.pack("!I", len(chunk)))
                    sock.sendall(chunk)
            sock.sendall(struct.pack("!I", 0))
            response = _read_clamd_response(sock)
    except (OSError, TimeoutError, socket.timeout):
        return ScanResult(
            status=SCAN_STATUS_FAILED,
            engine=SCAN_ENGINE_CLAMD,
            message="ClamAV daemon unavailable or timed out",
            scanned_at=now,
        )

    normalized = response.strip()
    upper_response = normalized.upper()
    if upper_response.endswith("OK") or " OK" in upper_response:
        return ScanResult(
            status=SCAN_STATUS_CLEAN,
            engine=SCAN_ENGINE_CLAMD,
            message="ClamAV scan passed",
            scanned_at=now,
        )
    if upper_response.endswith("FOUND") or " FOUND" in upper_response:
        return ScanResult(
            status=SCAN_STATUS_INFECTED,
            engine=SCAN_ENGINE_CLAMD,
            message="ClamAV detected a malware signature",
            scanned_at=now,
        )
    return ScanResult(
        status=SCAN_STATUS_FAILED,
        engine=SCAN_ENGINE_CLAMD,
        message=_clean_scan_message(f"ClamAV scan failed: {normalized or 'empty response'}"),
        scanned_at=now,
    )


def scan_file_with_provider(
    file_record: FileRecord,
    resolved_path: Path,
    *,
    provider: str,
    clamav_host: str,
    clamav_port: int,
    clamav_timeout_seconds: float,
) -> ScanResult:
    normalized_provider = provider.strip().lower()
    if normalized_provider == SCAN_ENGINE_MOCK:
        return scan_file_mock(file_record, resolved_path)
    if normalized_provider == SCAN_ENGINE_CLAMD:
        return scan_file_clamd(
            file_record,
            resolved_path,
            host=clamav_host,
            port=clamav_port,
            timeout_seconds=clamav_timeout_seconds,
        )
    return ScanResult(
        status=SCAN_STATUS_FAILED,
        engine=normalized_provider[:100] or "unknown",
        message="Unsupported scan provider",
        scanned_at=datetime.now(UTC),
    )


def build_manual_override_result(reason: str) -> ScanResult:
    return ScanResult(
        status=SCAN_STATUS_CLEAN,
        engine=SCAN_ENGINE_MANUAL_OVERRIDE,
        message=_clean_scan_message(f"Manual clean override; no ClamAV scan performed. Reason: {reason}"),
        scanned_at=datetime.now(UTC),
    )


def mark_file_scan_result(db: Session, file_record: FileRecord, result: ScanResult) -> FileRecord:
    file_record.scan_status = normalize_scan_status(result.status)
    file_record.scan_engine = result.engine[:100]
    file_record.scan_message = _clean_scan_message(result.message)
    file_record.scanned_at = result.scanned_at
    db.flush()
    return file_record

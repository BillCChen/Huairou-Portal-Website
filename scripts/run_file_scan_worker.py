#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, UTC
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / "apps/api-server"))

from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import settings
from app.db.models import AuditLog, FileRecord
from app.db.session import SessionLocal
from app.services.file_downloads import resolve_stored_path
from app.services.file_scanning import (
    SCAN_ENGINE_CLAMD,
    SCAN_ENGINE_MOCK,
    SCAN_STATUS_CLEAN,
    SCAN_STATUS_FAILED,
    SCAN_STATUS_INFECTED,
    SCAN_STATUSES,
    ScanResult,
    mark_file_scan_result,
    normalize_scan_status,
    scan_file_with_provider,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a one-shot file scan worker.")
    parser.add_argument("--provider", choices=[SCAN_ENGINE_CLAMD, SCAN_ENGINE_MOCK], default=settings.file_scan_provider)
    parser.add_argument("--limit", type=int, default=settings.file_scan_worker_limit)
    parser.add_argument("--retries", type=int, default=settings.file_scan_worker_retries)
    parser.add_argument("--retry-delay", type=float, default=settings.file_scan_worker_retry_delay_seconds)
    parser.add_argument("--status", choices=sorted(SCAN_STATUSES), default="pending")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def eligible_files(status: str, limit: int) -> list[FileRecord]:
    records: list[FileRecord] = []
    with SessionLocal() as db:
        for record in db.scalars(select(FileRecord).order_by(FileRecord.created_at.asc(), FileRecord.id.asc())):
            if normalize_scan_status(record.scan_status) == status:
                records.append(record)
                if len(records) >= limit:
                    break
    return records


def failed_result(provider: str, message: str) -> ScanResult:
    return ScanResult(status=SCAN_STATUS_FAILED, engine=provider, message=message, scanned_at=datetime.now(UTC))


def scan_record(record: FileRecord, provider: str, retries: int, retry_delay: float) -> tuple[ScanResult, int]:
    attempts = max(1, retries + 1)
    result = failed_result(provider, "Scan did not run")
    for attempt in range(1, attempts + 1):
        try:
            resolved_path = resolve_stored_path(record)
            result = scan_file_with_provider(
                record,
                resolved_path,
                provider=provider,
                clamav_host=settings.clamav_host,
                clamav_port=settings.clamav_port,
                clamav_timeout_seconds=settings.clamav_timeout_seconds,
            )
        except HTTPException:
            result = failed_result(provider, "Stored file path is not allowed")

        if result.status != SCAN_STATUS_FAILED or attempt == attempts:
            return result, attempt
        if retry_delay > 0:
            time.sleep(retry_delay)
    return result, attempts


def audit_worker_scan(db, record: FileRecord, result: ScanResult, attempts: int) -> None:
    scan_completed = result.status in {SCAN_STATUS_CLEAN, SCAN_STATUS_INFECTED}
    db.add(
        AuditLog(
            user_id=None,
            module="files",
            action="file_scan_worker",
            object_type="file",
            object_id=str(record.id),
            detail_json={
                "file_id": record.id,
                "scan_status": result.status,
                "scan_engine": result.engine,
                "scan_message": result.message,
                "attempts": attempts,
                "result": result.status,
            },
            result="success" if scan_completed else "failure",
            failure_reason=None if scan_completed else result.status,
        )
    )


def main() -> int:
    args = parse_args()
    if args.limit < 1:
        raise SystemExit("--limit must be at least 1")
    if args.retries < 0:
        raise SystemExit("--retries must be at least 0")
    if args.retry_delay < 0:
        raise SystemExit("--retry-delay must be at least 0")

    pending = eligible_files(args.status, args.limit)
    print(f"scan worker provider={args.provider} status={args.status} selected={len(pending)} dry_run={args.dry_run}")
    if args.dry_run:
        for record in pending:
            print(f"file id={record.id} status={normalize_scan_status(record.scan_status)} dry_run=yes")
        return 0

    processed = 0
    with SessionLocal() as db:
        for selected in pending:
            record = db.get(FileRecord, selected.id)
            if not record:
                continue
            result, attempts = scan_record(record, args.provider, args.retries, args.retry_delay)
            mark_file_scan_result(db, record, result)
            audit_worker_scan(db, record, result, attempts)
            db.commit()
            processed += 1
            print(f"file id={record.id} status={result.status} engine={result.engine} attempts={attempts}")
    print(f"scan worker completed processed={processed}")
    return 0


if __name__ == "__main__":
    os.chdir(ROOT_DIR)
    raise SystemExit(main())

"""Batch-load diagnostic TXT files into PostgreSQL.

Flow per file:
    hash check -> parser/export -> stage load -> data quality -> raw promotion
    -> source-file move -> best-effort temporary-output cleanup
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from src.db.database_creation import connection_kwargs, deploy_database_migrations

PARSER = ROOT / "src" / "pipeline" / "checkin_file_parser.py"

COLUMN_MAP = {
    "VIN": "vin",
    "FileName": "file_name",
    "FilePath": "file_path",
    "SW_I_Step": "sw_i_step",
    "SA_Codes": "sa_codes",
    "ECUName": "ecu_name",
    "HardwareVersion": "hardware_version",
    "BootloaderVersion": "bootloader_version",
    "SWVersion": "sw_version",
    "Coding": "coding",
    "DiagnosticAddress": "diagnostic_address",
    "CalibrationVersion": "calibration_version",
    "Network": "network",
    "SecureBoot": "secure_boot",
    "OTAState": "ota_state",
    "DTCCode": "dtc_code",
    "Description": "description",
    "FaultCategory": "fault_category",
    "NormalizedFaultCategory": "normalized_fault_category",
    "Status": "status",
    "OccurrenceCounter": "occurrence_counter",
    "AgingCounter": "aging_counter",
    "Priority": "priority",
    "HealingCounter": "healing_counter",
    "DebounceCounter": "debounce_counter",
    "Severity": "severity",
    "FirstDetected": "first_detected",
    "LastDetected": "last_detected",
    "ConfirmationState": "confirmation_state",
    "PossibleCause": "possible_cause",
    "RecommendedCheck": "recommended_check",
    "EventTimestamp": "event_timestamp",
    "RiskScore": "risk_score",
    "SignalName": "signal_name",
    "SignalValue": "signal_value",
}

CORE_DTC_COLUMNS = {
    "file_name",
    "sw_i_step",
    "ecu_name",
    "dtc_code",
    "description",
    "fault_category",
    "normalized_fault_category",
    "status",
    "occurrence_counter",
    "aging_counter",
    "priority",
    "healing_counter",
    "debounce_counter",
    "severity",
    "first_detected",
    "last_detected",
    "confirmation_state",
    "possible_cause",
    "recommended_check",
    "event_timestamp",
    "risk_score",
}


def configured_path(name: str, default: str) -> Path:
    """Resolve an environment path relative to the repository unless absolute."""
    value = Path(os.getenv(name, default)).expanduser()
    return value if value.is_absolute() else ROOT / value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def move_file(path: Path, destination: Path) -> Path:
    """Move a source file without overwriting an existing file."""
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / path.name
    counter = 1
    while target.exists():
        target = destination / f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    shutil.move(str(path), str(target))
    return target


def cleanup_temp_folder(temp_folder: Path | None) -> None:
    """Best-effort temporary-output cleanup with retries for Windows locks."""
    if temp_folder is None:
        return

    temp_folder = Path(temp_folder)
    if not temp_folder.exists():
        return

    max_attempts = int(os.getenv("TEMP_CLEANUP_ATTEMPTS", "5"))
    delay_seconds = float(os.getenv("TEMP_CLEANUP_DELAY_SECONDS", "2"))

    for attempt in range(1, max_attempts + 1):
        try:
            shutil.rmtree(temp_folder)
            logging.info("Temporary parser output removed: %s", temp_folder)
            return
        except PermissionError as error:
            if attempt < max_attempts:
                logging.warning(
                    "Temporary output is locked; cleanup attempt %s/%s failed for %s. "
                    "Retrying in %.1f seconds. Error: %s",
                    attempt,
                    max_attempts,
                    temp_folder,
                    delay_seconds,
                    error,
                )
                time.sleep(delay_seconds)
                continue
            logging.warning(
                "Temporary output remains locked after %s attempts: %s. "
                "The processing result is preserved; delete this folder manually later.",
                max_attempts,
                temp_folder,
            )
            return
        except OSError:
            logging.exception("Unable to remove temporary parser output: %s", temp_folder)
            return


def read_csv_output(folder: Path, name: str) -> pd.DataFrame:
    path = folder / "csv" / name
    if not path.exists():
        raise FileNotFoundError(f"Parser output is missing: {path}")
    return pd.read_csv(path, dtype=str, keep_default_na=False).rename(columns=COLUMN_MAP)


def integer_value(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def timestamp_value(value):
    parsed = pd.to_datetime(value, errors="coerce", utc=True)
    return None if pd.isna(parsed) else parsed.to_pydatetime()


def blank_to_none(value):
    return None if value is None or str(value).strip() == "" else value


def extended_values(row: pd.Series) -> dict:
    return {
        str(key): value
        for key, value in row.items()
        if key not in CORE_DTC_COLUMNS and blank_to_none(value) is not None
    }


def check_completed_duplicate(file_hash: str) -> bool:
    with psycopg.connect(**connection_kwargs()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM admin.file_inventory
                WHERE file_hash = %s
                  AND process_status = 'Completed'
                """,
                (file_hash,),
            )
            return cursor.fetchone() is not None


def run_parser(source: Path, output: Path) -> None:
    if not PARSER.exists():
        raise FileNotFoundError(f"Parser script not found: {PARSER}")

    output.mkdir(parents=True, exist_ok=False)
    logging.info("Running parser | file=%s | output=%s", source.name, output)
    subprocess.run(
        [
            sys.executable,
            str(PARSER),
            "--input",
            str(source),
            "--output",
            str(output),
        ],
        check=True,
    )


def read_parser_outputs(temp: Path):
    return (
        read_csv_output(temp, "parsed_report_header.csv"),
        read_csv_output(temp, "parsed_ecu_metadata.csv"),
        read_csv_output(temp, "parsed_dtc_events.csv"),
        read_csv_output(temp, "parsed_environment_signals.csv"),
    )


def load_file_transaction(
    source: Path,
    file_hash: str,
    report: pd.DataFrame,
    ecu: pd.DataFrame,
    dtc: pd.DataFrame,
    signals: pd.DataFrame,
    expected_signals: int,
) -> str:
    if len(report.index) != 1:
        raise ValueError(
            f"Expected exactly one report-header row for {source.name}; found {len(report.index)}."
        )

    with psycopg.connect(**connection_kwargs()) as connection:
        with connection.cursor() as cursor:
            row = report.iloc[0]
            cursor.execute(
                """
                INSERT INTO admin.file_inventory (
                    file_name, file_path, sw_i_step, file_size_bytes, file_hash,
                    processing_start_time, process_status
                )
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'Processing')
                ON CONFLICT (file_hash) DO UPDATE SET
                    file_name = EXCLUDED.file_name,
                    file_path = EXCLUDED.file_path,
                    sw_i_step = EXCLUDED.sw_i_step,
                    file_size_bytes = EXCLUDED.file_size_bytes,
                    processing_start_time = CURRENT_TIMESTAMP,
                    processing_end_time = NULL,
                    process_status = 'Processing',
                    error_message = NULL
                RETURNING file_id
                """,
                (
                    source.name,
                    str(source.resolve()),
                    blank_to_none(row.get("sw_i_step")),
                    source.stat().st_size,
                    file_hash,
                ),
            )
            file_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO admin.process_execution_log (file_id, process_name)
                VALUES (%s, %s)
                RETURNING process_run_id
                """,
                (file_id, f"Automated load: {source.name}"),
            )
            process_run_id = cursor.fetchone()[0]

            cursor.execute(
                """
                INSERT INTO stage.diagnostic_report (
                    process_run_id, file_id, file_name, file_path, vin, sw_i_step, sa_codes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    process_run_id,
                    file_id,
                    blank_to_none(row.get("file_name")),
                    blank_to_none(row.get("file_path")),
                    blank_to_none(row.get("vin")),
                    blank_to_none(row.get("sw_i_step")),
                    blank_to_none(row.get("sa_codes")),
                ),
            )

            for _, item in ecu.iterrows():
                cursor.execute(
                    """
                    INSERT INTO stage.ecu_version (
                        process_run_id, file_id, file_name, sw_i_step, ecu_name,
                        hardware_version, bootloader_version, sw_version, coding,
                        diagnostic_address, calibration_version, network, secure_boot, ota_state
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        process_run_id,
                        file_id,
                        blank_to_none(item.get("file_name")),
                        blank_to_none(item.get("sw_i_step")),
                        blank_to_none(item.get("ecu_name")),
                        blank_to_none(item.get("hardware_version")),
                        blank_to_none(item.get("bootloader_version")),
                        blank_to_none(item.get("sw_version")),
                        blank_to_none(item.get("coding")),
                        blank_to_none(item.get("diagnostic_address")),
                        blank_to_none(item.get("calibration_version")),
                        blank_to_none(item.get("network")),
                        blank_to_none(item.get("secure_boot")),
                        blank_to_none(item.get("ota_state")),
                    ),
                )

            for source_row_number, (_, item) in enumerate(dtc.iterrows(), 1):
                cursor.execute(
                    """
                    INSERT INTO stage.dtc_event (
                        process_run_id, file_id, source_row_number, file_name, sw_i_step,
                        ecu_name, dtc_code, description, fault_category,
                        normalized_fault_category, status, occurrence_counter, aging_counter,
                        priority, healing_counter, debounce_counter, severity, first_detected,
                        last_detected, confirmation_state, possible_cause, recommended_check,
                        event_timestamp, risk_score, extended_attributes
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        process_run_id,
                        file_id,
                        source_row_number,
                        blank_to_none(item.get("file_name")),
                        blank_to_none(item.get("sw_i_step")),
                        blank_to_none(item.get("ecu_name")),
                        blank_to_none(item.get("dtc_code")),
                        blank_to_none(item.get("description")),
                        blank_to_none(item.get("fault_category")),
                        blank_to_none(item.get("normalized_fault_category")),
                        blank_to_none(item.get("status")),
                        integer_value(item.get("occurrence_counter")),
                        integer_value(item.get("aging_counter")),
                        integer_value(item.get("priority")),
                        integer_value(item.get("healing_counter")),
                        integer_value(item.get("debounce_counter")),
                        blank_to_none(item.get("severity")),
                        timestamp_value(item.get("first_detected")),
                        timestamp_value(item.get("last_detected")),
                        blank_to_none(item.get("confirmation_state")),
                        blank_to_none(item.get("possible_cause")),
                        blank_to_none(item.get("recommended_check")),
                        timestamp_value(item.get("event_timestamp")),
                        integer_value(item.get("risk_score")),
                        Jsonb(extended_values(item)),
                    ),
                )

            for source_row_number, (_, item) in enumerate(signals.iterrows(), 1):
                cursor.execute(
                    """
                    INSERT INTO stage.environment_signal (
                        process_run_id, file_id, source_row_number, file_name, sw_i_step,
                        ecu_name, dtc_code, signal_name, signal_value, event_timestamp
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        process_run_id,
                        file_id,
                        source_row_number,
                        blank_to_none(item.get("file_name")),
                        blank_to_none(item.get("sw_i_step")),
                        blank_to_none(item.get("ecu_name")),
                        blank_to_none(item.get("dtc_code")),
                        blank_to_none(item.get("signal_name")),
                        blank_to_none(item.get("signal_value")),
                        timestamp_value(item.get("event_timestamp")),
                    ),
                )

            logging.info(
                "Stage counts | run=%s report=%s ecu=%s dtc=%s signals=%s",
                process_run_id,
                len(report.index),
                len(ecu.index),
                len(dtc.index),
                len(signals.index),
            )

            cursor.execute(
                "SELECT * FROM admin.run_data_quality_checks(%s, %s)",
                (process_run_id, expected_signals),
            )
            quality = cursor.fetchone()
            logging.info(
                "Quality result | run=%s total=%s info=%s warnings=%s errors=%s critical=%s status=%s",
                *quality,
            )

            if quality[6] == "Rejected":
                cursor.execute(
                    """
                    UPDATE admin.process_execution_log
                    SET end_time = CURRENT_TIMESTAMP,
                        process_status = 'Rejected',
                        rejected_records = %s,
                        error_message = 'Data-quality rejection'
                    WHERE process_run_id = %s
                    """,
                    (quality[4] + quality[5], process_run_id),
                )
                cursor.execute(
                    """
                    UPDATE admin.file_inventory
                    SET processing_end_time = CURRENT_TIMESTAMP,
                        process_status = 'Rejected',
                        error_message = 'Data-quality rejection'
                    WHERE file_id = %s
                    """,
                    (file_id,),
                )
                connection.commit()
                return "rejected"

            cursor.execute("CALL admin.promote_process_run(%s)", (process_run_id,))
            # Connection context commits accepted promotion on successful exit.
            return "completed"


def process_file(path: Path, args) -> str:
    file_hash = sha256(path)
    temp = None
    result = None

    try:
        logging.info("Starting file | name=%s | sha256=%s", path.name, file_hash)

        if check_completed_duplicate(file_hash):
            target = move_file(path, args.processed)
            logging.info("Duplicate skipped | source=%s | destination=%s", path, target)
            return "duplicate"

        run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp = args.output / path.stem / run_stamp

        run_parser(path, temp)
        report, ecu, dtc, signals = read_parser_outputs(temp)
        result = load_file_transaction(
            path,
            file_hash,
            report,
            ecu,
            dtc,
            signals,
            args.expected_signals,
        )

        destination = args.processed if result == "completed" else args.rejected
        target = move_file(path, destination)
        logging.info("File %s | source=%s | destination=%s", result, path, target)
        return result

    finally:
        cleanup_temp_folder(temp)


def configure_logging() -> None:
    log_dir = configured_path("LOG_PATH", "logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "postgres_batch_loader.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )


def main() -> int:
    configure_logging()
    deploy_database_migrations()

    parser = argparse.ArgumentParser(description="Load diagnostic TXT files into PostgreSQL.")
    parser.add_argument(
        "--input",
        type=Path,
        default=configured_path("INPUT_PATH", "Data/input/diagnostic_reports"),
    )
    parser.add_argument(
        "--expected-signals",
        type=int,
        default=int(os.getenv("EXPECTED_SIGNALS_PER_DTC", "0")),
    )
    args = parser.parse_args()

    if not args.input.is_absolute():
        args.input = ROOT / args.input

    args.output = configured_path("OUTPUT_PATH", "output") / "batch_temp"
    args.processed = configured_path("PROCESSED_PATH", "Data/input/processed")
    args.rejected = configured_path("REJECTED_PATH", "Data/input/rejected")
    args.failed = configured_path("FAILED_PATH", "Data/input/failed")

    for folder in (args.output, args.processed, args.rejected, args.failed):
        folder.mkdir(parents=True, exist_ok=True)

    if args.input.is_file():
        files = [args.input]
    elif args.input.is_dir():
        files = sorted(args.input.glob("*.txt"))
    else:
        logging.error("Input path does not exist: %s", args.input)
        return 3

    if not files:
        logging.info("No TXT files found in: %s", args.input)
        return 0

    counts = {"completed": 0, "rejected": 0, "duplicate": 0, "failed": 0}

    for source in files:
        try:
            counts[process_file(source, args)] += 1
        except Exception:
            logging.exception("Failed %s", source.name)
            if source.exists():
                target = move_file(source, args.failed)
                logging.error("Failed source moved to: %s", target)
            counts["failed"] += 1

    logging.info("Summary %s", counts)
    if counts["failed"]:
        return 2
    if counts["rejected"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

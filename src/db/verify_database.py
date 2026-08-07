import psycopg
from database_creation import connection_kwargs

QUERIES = {
    "reports": "SELECT COUNT(*) FROM raw.diagnostic_report",
    "ecus": "SELECT COUNT(*) FROM raw.ecu_version",
    "dtcs": "SELECT COUNT(*) FROM raw.dtc_event",
    "signals": "SELECT COUNT(*) FROM raw.environment_signal",
    "completed_files": "SELECT COUNT(*) FROM admin.file_inventory WHERE process_status='Completed'",
    "rejected_files": "SELECT COUNT(*) FROM admin.file_inventory WHERE process_status='Rejected'",
}


def main():
    with psycopg.connect(**connection_kwargs()) as connection:
        with connection.cursor() as cursor:
            for label, query in QUERIES.items():
                cursor.execute(query)
                print(f"{label}: {cursor.fetchone()[0]}")
            cursor.execute("SELECT COUNT(*) FROM reporting.vw_dtc_detail")
            dtc_view = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM raw.dtc_event")
            raw_dtc = cursor.fetchone()[0]
            if dtc_view != raw_dtc:
                raise RuntimeError(f"DTC reporting reconciliation failed: view={dtc_view}, raw={raw_dtc}")
            print("DTC reporting reconciliation: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Upload generated files to a Snowflake stage and COPY them into RAW tables.

Prerequisite: run sql/01_setup.sql, 02_tables.sql and the stage/file-format part of 03_load.sql.

Run:
    python -m analytics_cloud_lab.loader --data-dir data
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import SnowflakeSettings
from .snowflake_client import SnowflakeClient

log = logging.getLogger(__name__)
STAGE = "@MAC_LAB.RAW.LAB_STAGE"
CSV_TABLES = ["experiences", "sessions", "page_views", "offers", "conversions"]


def load_all(sf: SnowflakeClient, data_dir: Path) -> None:
    for table in CSV_TABLES:
        sf.put(data_dir / f"{table}.csv", f"{STAGE}/{table}/")
        sf.execute(f"TRUNCATE TABLE MAC_LAB.RAW.{table.upper()}")
        rows = sf.query(
            f"COPY INTO MAC_LAB.RAW.{table.upper()} FROM {STAGE}/{table}/ "
            "FILE_FORMAT = (FORMAT_NAME = 'MAC_LAB.RAW.CSV_FF') ON_ERROR = 'ABORT_STATEMENT' FORCE = TRUE"
        )
        loaded = sum(int(r.get("rows_loaded", 0) or 0) for r in rows)
        log.info("%-12s loaded %s rows", table, loaded)

    sf.put(data_dir / "events.jsonl", f"{STAGE}/events/")
    sf.execute("TRUNCATE TABLE MAC_LAB.RAW.EVENTS_RAW")
    sf.execute(
        "COPY INTO MAC_LAB.RAW.EVENTS_RAW (payload, file_name) "
        f"FROM (SELECT $1, METADATA$FILENAME FROM {STAGE}/events/) "
        "FILE_FORMAT = (FORMAT_NAME = 'MAC_LAB.RAW.JSON_FF') FORCE = TRUE"
    )
    log.info("events loaded")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load lab data into Snowflake")
    parser.add_argument("--data-dir", default="data", type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    with SnowflakeClient(SnowflakeSettings.from_env()) as sf:
        load_all(sf, args.data_dir)


if __name__ == "__main__":
    main()

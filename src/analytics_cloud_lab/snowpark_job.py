"""Build the variant summary with the Snowpark DataFrame API (runs inside Snowflake).

Run:
    pip install -e ".[snowflake]"
    python -m analytics_cloud_lab.snowpark_job
"""

from __future__ import annotations

import logging

from .config import SnowflakeSettings

log = logging.getLogger(__name__)
TARGET = "MAC_LAB.ANALYTICS.VARIANT_SUMMARY_SNOWPARK"


def build_summary(session):
    from snowflake.snowpark import Window
    from snowflake.snowpark.functions import coalesce, col, count, iff, lit, row_number
    from snowflake.snowpark.functions import sum as sum_

    offers = session.table("MAC_LAB.RAW.OFFERS")
    w = Window.partition_by("SESSION_ID", "EXPERIENCE_ID").order_by(col("FIRST_QUALIFIED_TS"))
    first = offers.with_column("RN", row_number().over(w)).filter(col("RN") == 1).drop("RN")

    conv = session.table("MAC_LAB.RAW.CONVERSIONS").select(
        col("SESSION_ID").alias("C_SESSION_ID"), col("ORDER_ID"), col("REVENUE"), col("CONVERSION_TS")
    )
    joined = first.join(
        conv,
        (col("SESSION_ID") == col("C_SESSION_ID")) & (col("CONVERSION_TS") >= col("FIRST_QUALIFIED_TS")),
        "left",
    )
    per_session = joined.group_by("CLIENT_ID", "EXPERIENCE_ID", "VARIANT_ID", "SESSION_ID").agg(
        count("ORDER_ID").alias("ORDERS"),
        sum_(coalesce(col("REVENUE"), lit(0))).alias("REVENUE"),
    )
    return per_session.group_by("CLIENT_ID", "EXPERIENCE_ID", "VARIANT_ID").agg(
        count(lit(1)).alias("SESSIONS"),
        sum_(iff(col("ORDERS") > 0, lit(1), lit(0))).alias("CONVERSIONS"),
        sum_("REVENUE").alias("TOTAL_REVENUE"),
    )


def main() -> None:
    from snowflake.snowpark import Session

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    session = Session.builder.configs(SnowflakeSettings.from_env().as_connector_kwargs()).create()
    try:
        df = build_summary(session)
        df.show()
        df.write.save_as_table(TARGET, mode="overwrite")
        log.info("Saved %s", TARGET)
    finally:
        session.close()


if __name__ == "__main__":
    main()

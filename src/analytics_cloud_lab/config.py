"""Configuration loaded from environment variables (or a local .env file)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:  # python-dotenv is optional
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


@dataclass(frozen=True)
class SnowflakeSettings:
    """Connection settings for Snowflake.

    Prefer key-pair auth (SNOWFLAKE_PRIVATE_KEY_FILE) or SSO
    (SNOWFLAKE_AUTHENTICATOR=externalbrowser) over plain passwords.
    """

    account: str
    user: str
    role: str = "LAB_ENGINEER"
    warehouse: str = "LAB_WH"
    database: str = "MAC_LAB"
    schema: str = "RAW"
    password: str | None = field(default=None, repr=False)
    authenticator: str | None = None
    private_key_file: str | None = None

    @classmethod
    def from_env(cls) -> SnowflakeSettings:
        missing = [v for v in ("SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER") if not os.getenv(v)]
        if missing:
            raise RuntimeError(f"Missing environment variables: {', '.join(missing)}")
        return cls(
            account=os.environ["SNOWFLAKE_ACCOUNT"],
            user=os.environ["SNOWFLAKE_USER"],
            role=os.getenv("SNOWFLAKE_ROLE", "LAB_ENGINEER"),
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE", "LAB_WH"),
            database=os.getenv("SNOWFLAKE_DATABASE", "MAC_LAB"),
            schema=os.getenv("SNOWFLAKE_SCHEMA", "RAW"),
            password=os.getenv("SNOWFLAKE_PASSWORD"),
            authenticator=os.getenv("SNOWFLAKE_AUTHENTICATOR"),
            private_key_file=os.getenv("SNOWFLAKE_PRIVATE_KEY_FILE"),
        )

    def as_connector_kwargs(self) -> dict:
        """Keyword arguments accepted by snowflake.connector.connect and Snowpark."""
        kwargs = {
            "account": self.account,
            "user": self.user,
            "role": self.role,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
        }
        if self.private_key_file:
            kwargs["private_key_file"] = self.private_key_file
        elif self.authenticator:
            kwargs["authenticator"] = self.authenticator
        elif self.password:
            kwargs["password"] = self.password
        return kwargs

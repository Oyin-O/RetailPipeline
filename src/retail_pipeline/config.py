"""Runtime settings, read from the environment."""

import os
from dataclasses import dataclass
from pathlib import Path

# No password here: it comes from the PGPASSWORD environment variable, or a full OLTP_DSN.
DEFAULT_OLTP_DSN = "postgresql://retail@localhost:5432/retail"
DEFAULT_DATA_DIR = "data"


@dataclass(frozen=True)
class Settings:
    oltp_dsn: str
    data_dir: Path

    @property
    def bronze_dir(self) -> Path:
        return self.data_dir / "bronze"

    @property
    def silver_dir(self) -> Path:
        return self.data_dir / "silver"

    @property
    def rejects_dir(self) -> Path:
        return self.data_dir / "rejects"

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state" / "watermarks.json"

    @property
    def warehouse_path(self) -> Path:
        return self.data_dir / "warehouse.duckdb"


def load_settings() -> Settings:
    return Settings(
        oltp_dsn=os.environ.get("OLTP_DSN", DEFAULT_OLTP_DSN),
        data_dir=Path(os.environ.get("RETAIL_DATA_DIR", DEFAULT_DATA_DIR)),
    )

"""Watermark store: the highest updated_at already extracted, per OLTP table."""

import json
import os
from datetime import datetime
from pathlib import Path


class WatermarkStore:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def get(self, table: str) -> datetime | None:
        value = self._load().get(table)
        return None if value is None else datetime.fromisoformat(value)

    def set(self, table: str, watermark: datetime) -> None:
        if watermark.tzinfo is None:
            raise ValueError("watermark must be timezone-aware")
        marks = self._load()
        marks[table] = watermark.isoformat()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(marks, indent=2, sort_keys=True))
        os.replace(tmp, self.path)

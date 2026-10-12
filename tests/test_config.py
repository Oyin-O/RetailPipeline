from pathlib import Path

from psycopg.conninfo import conninfo_to_dict

from retail_pipeline.config import DEFAULT_OLTP_DSN, load_settings


def test_default_dsn_carries_no_password():
    assert "password" not in conninfo_to_dict(DEFAULT_OLTP_DSN)


def test_settings_come_from_the_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("OLTP_DSN", "postgresql://reader@db.internal:5432/shop")
    monkeypatch.setenv("RETAIL_DATA_DIR", str(tmp_path))

    settings = load_settings()

    assert settings.oltp_dsn == "postgresql://reader@db.internal:5432/shop"
    assert settings.data_dir == tmp_path


def test_settings_fall_back_to_defaults(monkeypatch):
    monkeypatch.delenv("OLTP_DSN", raising=False)
    monkeypatch.delenv("RETAIL_DATA_DIR", raising=False)

    settings = load_settings()

    assert settings.oltp_dsn == DEFAULT_OLTP_DSN
    assert settings.data_dir == Path("data")

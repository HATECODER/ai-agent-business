import psycopg
import pytest

from scripts.configure_staging_database_url import _build_url, _verify_connection


def test_session_pooler_url_encodes_password_and_requires_tls():
    url = _build_url(
        "postgresql://postgres.project:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:5432/postgres",
        "p@ss/word",
    )
    assert "p%40ss%2Fword" in url
    assert url.endswith("?sslmode=require")


def test_connection_verification_suppresses_driver_details(monkeypatch):
    def fail(*_args, **_kwargs):
        raise psycopg.OperationalError("private host and credential details")

    monkeypatch.setattr(psycopg, "connect", fail)
    with pytest.raises(RuntimeError) as raised:
        _verify_connection(
            "postgresql+psycopg://postgres.project:secret@host.pooler.supabase.com:5432/postgres?sslmode=require"
        )
    assert "private host" not in str(raised.value)
    assert "secret" not in str(raised.value)
    assert "Session pooler" in str(raised.value)

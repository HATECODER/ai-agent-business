import pytest

from database.seed import seed_database


@pytest.fixture
def seeded_db(tmp_path):
    path = tmp_path / "test.sqlite3"
    seed_database(path)
    return path

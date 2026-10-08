from database.db import connect
from services.recovery import backup_database, logical_snapshot, restore_database


def test_online_backup_and_separate_restore_match_logically(seeded_db, tmp_path):
    backup = tmp_path / "backup.sqlite3"
    restored = tmp_path / "restored.sqlite3"
    expected = backup_database(seeded_db, backup)

    with connect(seeded_db) as db:
        db.execute("UPDATE inventory SET quantity = quantity + 1 WHERE id = 1")
    assert logical_snapshot(seeded_db) != expected

    actual = restore_database(backup, restored)
    assert actual == expected
    assert logical_snapshot(restored) == expected


def test_backup_and_restore_refuse_implicit_overwrite(seeded_db, tmp_path):
    backup = tmp_path / "backup.sqlite3"
    target = tmp_path / "target.sqlite3"
    backup_database(seeded_db, backup)
    target.write_bytes(b"do-not-overwrite")

    try:
        restore_database(backup, target)
    except FileExistsError:
        pass
    else:
        raise AssertionError("restore must require explicit replacement")
    assert target.read_bytes() == b"do-not-overwrite"

import sqlite3

import pytest

from db_safety import backup_database, connect, restore_database, validate_backup
from database import init_db
from auth_service import AuthService


def test_first_login_requires_rotation(temp_db_path):
    auth = AuthService(temp_db_path)
    result = auth.authenticate('admin', 'admin123')
    assert result['user']['must_change_password']
    uid = result['user']['id']
    with pytest.raises(ValueError):
        auth.change_password(uid, 'wrong', 'long-and-secure-password')
    with pytest.raises(ValueError):
        auth.change_password(uid, 'admin123', 'short')
    auth.change_password(uid, 'admin123', 'long-and-secure-password')
    assert not auth.authenticate('admin', 'long-and-secure-password')['user']['must_change_password']
    assert not auth.authenticate('admin', 'admin123')['success']
    init_db(temp_db_path)
    assert not auth.authenticate('admin', 'long-and-secure-password')['user']['must_change_password']


def test_foreign_key_cascade(temp_db_path):
    with connect(temp_db_path) as conn:
        assert conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        cur = conn.execute("INSERT INTO CrewWages (Name) VALUES ('Sailor')")
        crew_id = cur.lastrowid
        conn.execute('INSERT INTO crew_documents (crew_id, doc_type, expiry_date) VALUES (?, ?, ?)',
                     (crew_id, 'Passport', '2030-01-01'))
        conn.execute('DELETE FROM CrewWages WHERE No=?', (crew_id,))
        assert conn.execute('SELECT count(*) FROM crew_documents').fetchone()[0] == 0


def test_wal_backup_and_restore(temp_db_path, tmp_path):
    backup = str(tmp_path / 'backup.db')
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute("INSERT INTO CrewWages (Name) VALUES ('Saved')")
    backup_database(temp_db_path, backup)
    validate_backup(backup)
    with sqlite3.connect(temp_db_path) as conn:
        conn.execute("INSERT INTO CrewWages (Name) VALUES ('Not saved')")
    safety = restore_database(backup, temp_db_path)
    assert safety is not None
    with sqlite3.connect(temp_db_path) as conn:
        assert conn.execute('SELECT Name FROM CrewWages').fetchall() == [('Saved',)]
    with sqlite3.connect(safety) as conn:
        assert conn.execute('SELECT count(*) FROM CrewWages').fetchone()[0] == 2


def test_invalid_backup_does_not_replace_database(temp_db_path, tmp_path):
    bad = tmp_path / 'invalid.db'
    bad.write_text('invalid')
    with pytest.raises(sqlite3.DatabaseError):
        restore_database(str(bad), temp_db_path)
    validate_backup(temp_db_path)

"""SQLite connection and consistent backup helpers."""
import os
import sqlite3
import tempfile


def connect(path):
    conn = sqlite3.connect(path)
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def validate_backup(path):
    # Read-only: never create a missing database by accident.
    with sqlite3.connect(f'file:{os.path.abspath(path)}?mode=ro', uri=True) as conn:
        if conn.execute('PRAGMA integrity_check').fetchone()[0].lower() != 'ok':
            raise ValueError('Database integrity check failed')
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if not {'users', 'CrewWages', 'payroll_history'}.issubset(tables):
            raise ValueError('Missing required payroll tables')


def backup_database(source, destination):
    """Create an atomic, consistent snapshot, including committed WAL transactions."""
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    directory = os.path.dirname(os.path.abspath(destination))
    fd, temporary = tempfile.mkstemp(prefix='.payroll-backup-', suffix='.db', dir=directory)
    os.close(fd)
    try:
        with sqlite3.connect(source) as src, sqlite3.connect(temporary) as dst:
            src.backup(dst)
        validate_backup(temporary)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def restore_database(source, destination):
    """Validate first, then restore through SQLite's backup API; return a safety copy path."""
    if os.path.abspath(source) == os.path.abspath(destination):
        raise ValueError('Source and destination must differ')
    validate_backup(source)
    safety_copy = destination + '.before_restore'
    if os.path.exists(destination):
        backup_database(destination, safety_copy)
    # Backup API copies into the existing database safely even in WAL mode.
    with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
        src.backup(dst)
    return safety_copy if os.path.exists(safety_copy) else None

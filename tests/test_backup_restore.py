# tests/test_backup_restore.py
import pytest
import sqlite3
import shutil
import os

class TestBackupAndRestore:
    """اختبارات آلية النسخ الاحتياطي وفحص السلامة والاستعادة"""

    def test_backup_creates_exact_copy(self, temp_db_path, tmp_path):
        backup_file = str(tmp_path / "backup_test.db")
        shutil.copy2(temp_db_path, backup_file)

        assert os.path.exists(backup_file)
        assert os.path.getsize(backup_file) > 0

        # فحص السلامة للنسخة الاحتياطية
        with sqlite3.connect(backup_file) as conn:
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            assert integrity[0].lower() == "ok"

    def test_integrity_check_detects_corrupt_file(self, tmp_path):
        fake_db = str(tmp_path / "corrupt.db")
        with open(fake_db, "wb") as f:
            f.write(b"NOT A SQLITE FILE HEADER TEST DATA 123456789")

        is_valid = False
        try:
            with sqlite3.connect(fake_db) as conn:
                res = conn.execute("PRAGMA integrity_check").fetchone()
                if res and res[0].lower() == "ok":
                    is_valid = True
        except Exception:
            is_valid = False

        assert is_valid is False

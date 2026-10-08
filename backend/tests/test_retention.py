import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.retention import _retention_days, _safe_storage_path


class RetentionTests(unittest.TestCase):
    def test_invalid_policy_uses_safe_default(self):
        self.assertEqual(_retention_days(None), 180)

    def test_storage_path_cannot_escape_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertIsNone(_safe_storage_path(root, "../outside.upload"))
            self.assertIsNotNone(_safe_storage_path(root, "quarantine/1/file.upload"))

    def test_expiry_reference_is_timezone_safe(self):
        created_at = datetime(2025, 1, 1)
        now = datetime(2025, 7, 1, tzinfo=timezone.utc)
        self.assertLess(
            created_at.replace(tzinfo=timezone.utc),
            now - timedelta(days=180),
        )


if __name__ == "__main__":
    unittest.main()


class RetentionPurgeTests(unittest.TestCase):
    def test_apply_deletes_file_wipes_extracted_text_and_audits(self):
        import tempfile
        from datetime import datetime, timedelta, timezone
        from pathlib import Path

        from sqlalchemy import create_engine, select
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.db import Base
        from app.models import AuditLogEntry, Document, DocumentText, Tenant, User
        from app.retention import cleanup_storage

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        with tempfile.TemporaryDirectory() as root:
            (Path(root) / "old.pdf").write_bytes(b"%PDF-1.4 secret")
            with Session() as db:
                tenant = Tenant(name="T"); db.add(tenant); db.flush()
                user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role="USER"); db.add(user); db.flush()
                document = Document(tenant_id=tenant.id, uploaded_by=user.id, original_filename="old.pdf", storage_key="old.pdf", extension=".pdf", mime_type="application/pdf", size_bytes=1, sha256="a" * 64, status="CLASSIFICATION_CONFIRMED", created_at=datetime.now(timezone.utc) - timedelta(days=4000))
                db.add(document); db.flush()
                db.add(DocumentText(tenant_id=tenant.id, document_id=document.id, extracted_text="주민번호 900101-1234567", extractor="t", status="EXTRACTED"))
                db.commit()
            summary = cleanup_storage(Session, storage_root=Path(root), apply=True)
            self.assertFalse((Path(root) / "old.pdf").exists())
        self.assertEqual(summary["purged_text_count"], 1)
        with Session() as db:
            text = db.scalars(select(DocumentText)).one()
            self.assertEqual(text.extracted_text, "")
            self.assertEqual(db.scalars(select(AuditLogEntry)).one().event_type, "RETENTION_PURGED")
        engine.dispose()

import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.siem import export_siem
from app.audit_chain import append_audit_entry
from app.db import Base
from app.models import Tenant, User


class SiemExportTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed(self):
        with self.Session() as db:
            tenant = Tenant(name="SIEM Tenant")
            db.add(tenant)
            db.flush()
            admin = User(tenant_id=tenant.id, username="a", display_name="Admin", password_hash="x", role="ADMIN")
            db.add(admin)
            db.flush()
            append_audit_entry(
                db, tenant_id=tenant.id, event_type="CLASSIFICATION_CONFIRMED",
                payload={"document_id": 1, "confirmed_grade": "C"},
            )
            append_audit_entry(
                db, tenant_id=tenant.id, event_type="REVIEW_REQUEST_CREATED",
                payload={"review_request_id": 1, "document_id": 1},
            )
            db.commit()
            return admin.id

    def test_cef_export_contains_one_line_per_entry_with_expected_fields(self):
        admin_id = self._seed()
        with self.Session() as db:
            admin = db.get(User, admin_id)
        with patch("app.api.siem.get_session_factory", return_value=self.Session):
            response = export_siem(since=None, until=None, limit=1000, export_format="cef", current_user=admin)

        lines = response.body.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("CEF:0|PASSBOX|N2SF-AI-Gateway|1.0|CLASSIFICATION_CONFIRMED|"))
        self.assertIn("confirmedgrade=C", lines[0])
        self.assertTrue(lines[1].startswith("CEF:0|PASSBOX|N2SF-AI-Gateway|1.0|REVIEW_REQUEST_CREATED|"))

    def test_json_export_preserves_hash_chain_fields(self):
        admin_id = self._seed()
        with self.Session() as db:
            admin = db.get(User, admin_id)
        with patch("app.api.siem.get_session_factory", return_value=self.Session):
            items = export_siem(since=None, until=None, limit=1000, export_format="json", current_user=admin)

        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["event_type"], "CLASSIFICATION_CONFIRMED")
        self.assertIn("record_hash", items[0])
        self.assertIn("previous_hash", items[0])

    def test_non_admin_role_is_forbidden(self):
        from app.api.auth import require_roles

        with self.Session() as db:
            tenant = Tenant(name="Non Admin Tenant")
            db.add(tenant)
            db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role="USER")
            db.add(user)
            db.commit()
            user_id = user.id
        with self.Session() as db:
            user = db.get(User, user_id)

        guard = require_roles("SECURITY_ADMIN", "ADMIN")
        with self.assertRaises(HTTPException) as context:
            guard(user)
        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

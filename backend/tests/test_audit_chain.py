import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.audit_chain import GENESIS_HASH, append_audit_entry, verify_chain
from app.db import Base
from app.models import AuditLogEntry, Tenant


class AuditChainTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            tenant = Tenant(name="감사로그 테스트 기관")
            db.add(tenant)
            db.commit()
            self.tenant_id = tenant.id

    def tearDown(self):
        self.engine.dispose()

    def test_first_entry_chains_from_genesis(self):
        with self.Session() as db:
            entry = append_audit_entry(
                db,
                tenant_id=self.tenant_id,
                event_type="DOCUMENT_UPLOADED",
                payload={"file_name": "report.pdf"},
            )
            db.commit()

            self.assertEqual(entry.sequence, 1)
            self.assertEqual(entry.previous_hash, GENESIS_HASH)
            self.assertEqual(len(entry.record_hash), 64)

    def test_consecutive_entries_link_by_hash(self):
        with self.Session() as db:
            first = append_audit_entry(
                db, tenant_id=self.tenant_id, event_type="DOCUMENT_UPLOADED", payload={"a": 1}
            )
            second = append_audit_entry(
                db, tenant_id=self.tenant_id, event_type="CLASSIFICATION_CONFIRMED", payload={"grade": "S"}
            )
            db.commit()

            self.assertEqual(second.sequence, 2)
            self.assertEqual(second.previous_hash, first.record_hash)

    def test_tenants_have_independent_chains(self):
        with self.Session() as db:
            other = Tenant(name="다른 기관")
            db.add(other)
            db.flush()

            append_audit_entry(db, tenant_id=self.tenant_id, event_type="X", payload={})
            first_of_other = append_audit_entry(db, tenant_id=other.id, event_type="X", payload={})
            db.commit()

            self.assertEqual(first_of_other.sequence, 1)
            self.assertEqual(first_of_other.previous_hash, GENESIS_HASH)

    def test_verify_chain_passes_for_untouched_log(self):
        with self.Session() as db:
            for i in range(5):
                append_audit_entry(
                    db, tenant_id=self.tenant_id, event_type="STEP", payload={"i": i}
                )
            db.commit()
            entries = list(
                db.query(AuditLogEntry).filter(AuditLogEntry.tenant_id == self.tenant_id)
            )

        result = verify_chain(entries)

        self.assertTrue(result.valid)
        self.assertEqual(result.checked_count, 5)
        self.assertIsNone(result.broken_at_sequence)

    def test_verify_chain_detects_a_tampered_payload(self):
        with self.Session() as db:
            for i in range(3):
                append_audit_entry(
                    db, tenant_id=self.tenant_id, event_type="STEP", payload={"i": i}
                )
            db.commit()
            entries = list(
                db.query(AuditLogEntry).filter(AuditLogEntry.tenant_id == self.tenant_id)
            )

        # Simulate someone editing row #2's payload directly in the database
        # after the fact, without recomputing the hash chain.
        entries[1].payload = {"i": 999}

        result = verify_chain(entries)

        self.assertFalse(result.valid)
        self.assertEqual(result.broken_at_sequence, 2)
        self.assertIn("edited", result.reason)

    def test_verify_chain_detects_a_deleted_entry(self):
        with self.Session() as db:
            for i in range(3):
                append_audit_entry(
                    db, tenant_id=self.tenant_id, event_type="STEP", payload={"i": i}
                )
            db.commit()
            entries = list(
                db.query(AuditLogEntry).filter(AuditLogEntry.tenant_id == self.tenant_id)
            )

        # Simulate someone deleting the middle row: sequence 3 now points at
        # sequence 1's hash instead of sequence 2's.
        remaining = [entries[0], entries[2]]

        result = verify_chain(remaining)

        self.assertFalse(result.valid)
        self.assertEqual(result.broken_at_sequence, 3)


if __name__ == "__main__":
    unittest.main()

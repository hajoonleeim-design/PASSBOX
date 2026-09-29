import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.operations import _dashboard_response, _p95, verify_audit_chain
from app.audit_chain import append_audit_entry
from app.db import Base
from app.models import AuditLogEntry, Tenant, User


UTC = timezone.utc


def item(**values):
    return SimpleNamespace(**values)


class OperationsDashboardTests(unittest.TestCase):
    def test_empty_tenant_returns_zeroed_dashboard(self):
        dashboard = _dashboard_response(
            requests=[],
            jobs=[],
            documents=[],
            decisions=[],
            transmissions=[],
            approvals=[],
            policy=None,
            now=datetime(2026, 9, 18, 9, 0, tzinfo=UTC),
        )

        self.assertEqual(dashboard.summary.totalRequests, 0)
        self.assertEqual(dashboard.summary.processingRequests, 0)
        self.assertEqual(dashboard.summary.successRate, 0.0)
        self.assertEqual(dashboard.queue.totalQueued, 0)
        self.assertEqual(dashboard.providers, [])
        self.assertEqual(dashboard.incidents, [])

    def test_dashboard_aggregates_real_pipeline_states(self):
        base = datetime(2026, 9, 18, 8, 0, tzinfo=UTC)
        requests = [
            item(id=1, document_id=10, created_at=base, status="RECEIVED"),
            item(id=2, document_id=11, created_at=base, status="RECEIVED"),
            item(id=3, document_id=12, created_at=base, status="RECEIVED"),
            item(id=4, document_id=13, created_at=base, status="RECEIVED"),
        ]
        documents = [
            item(id=10, original_filename="secret.pdf"),
            item(id=11, original_filename="sensitive.pdf"),
            item(id=12, original_filename="failed.pdf"),
            item(id=13, original_filename="public.pdf"),
        ]
        jobs = [
            item(id=1, request_id=1, status="COMPLETED", created_at=base, updated_at=base + timedelta(minutes=2)),
            item(id=2, request_id=2, status="QUEUED", created_at=base, updated_at=base),
            item(id=3, request_id=3, status="FAILED", created_at=base, updated_at=base + timedelta(minutes=1)),
            item(id=4, request_id=4, status="COMPLETED", created_at=base, updated_at=base + timedelta(minutes=3)),
        ]
        decisions = [
            item(id=1, document_id=10, confirmed_grade="C", created_at=base),
            item(id=2, document_id=11, confirmed_grade="S", created_at=base),
            item(id=3, document_id=12, confirmed_grade="O", created_at=base),
            item(id=4, document_id=13, confirmed_grade="O", created_at=base),
        ]
        transmissions = [
            item(
                id=1,
                document_id=11,
                provider="openai",
                status="WAITING_APPROVAL",
                policy_decision="APPROVAL_REQUIRED",
                created_at=base + timedelta(minutes=4),
                error_message=None,
            ),
            item(
                id=2,
                document_id=12,
                provider="openai",
                status="FAILED",
                policy_decision="ALLOWED",
                created_at=base + timedelta(minutes=5),
                error_message="Gateway 장애",
            ),
            item(
                id=3,
                document_id=13,
                provider="gemini",
                status="COMPLETED",
                policy_decision="ALLOWED",
                created_at=base + timedelta(minutes=6),
                error_message=None,
            ),
        ]
        approvals = [item(id=1, gateway_transmission_id=1, status="PENDING", created_at=base + timedelta(minutes=4))]
        policy = item(model_allowlist=[{"provider": "local", "enabled": True}])

        dashboard = _dashboard_response(
            requests=requests,
            jobs=jobs,
            documents=documents,
            decisions=decisions,
            transmissions=transmissions,
            approvals=approvals,
            policy=policy,
            now=base + timedelta(minutes=10),
        )

        self.assertEqual(dashboard.summary.totalRequests, 4)
        self.assertEqual(dashboard.summary.completedRequests, 1)
        self.assertEqual(dashboard.summary.blockedRequests, 1)
        self.assertEqual(dashboard.summary.failedRequests, 1)
        self.assertEqual(dashboard.summary.processingRequests, 1)
        self.assertEqual(dashboard.summary.successRate, 25.0)
        self.assertEqual(dashboard.queue.waitingApproval, 1)
        self.assertEqual(dashboard.queue.totalQueued, 1)
        self.assertEqual(dashboard.performance.throughputPerHour, 1)
        self.assertEqual([(item.grade, item.count) for item in dashboard.csoDistribution], [("C", 1), ("S", 1), ("O", 2)])
        self.assertEqual(dashboard.providers[0].providerId, "gemini")
        self.assertEqual(dashboard.providers[1].status, "UNKNOWN")
        self.assertEqual(dashboard.providers[2].status, "DOWN")
        self.assertEqual(dashboard.incidents[0].incidentId, "INC-TRANSMISSION-2")

    def test_p95_uses_upper_percentile_sample(self):
        self.assertEqual(_p95([100, 200, 300, 400, 500]), 400)

    def test_prompt_injection_blocks_appear_as_resolved_security_incidents(self):
        base = datetime(2026, 9, 18, 8, 0, tzinfo=UTC)
        requests = [item(id=1, document_id=10, created_at=base, status="RECEIVED")]
        documents = [item(id=10, original_filename="poisoned.pdf")]
        jobs = [item(id=1, request_id=1, status="BLOCKED", created_at=base, updated_at=base)]
        decisions = [item(id=1, document_id=10, confirmed_grade="O", created_at=base)]
        transmissions = [
            item(
                id=1,
                document_id=10,
                provider="openai",
                status="BLOCKED",
                policy_decision="PROMPT_INJECTION_BLOCKED",
                created_at=base + timedelta(minutes=1),
                error_message="문서 본문에서 프롬프트 인젝션 시도가 탐지되어 전송을 차단했습니다.",
            )
        ]

        dashboard = _dashboard_response(
            requests=requests,
            jobs=jobs,
            documents=documents,
            decisions=decisions,
            transmissions=transmissions,
            approvals=[],
            policy=None,
            now=base + timedelta(minutes=5),
        )

        self.assertEqual(len(dashboard.incidents), 1)
        incident = dashboard.incidents[0]
        self.assertEqual(incident.incidentId, "INC-INJECTION-1")
        self.assertEqual(incident.severity, "MEDIUM")
        self.assertEqual(incident.status, "RESOLVED")
        self.assertIsNotNone(incident.resolvedAt)
        self.assertEqual(incident.relatedJobId, "JOB-1")


class AuditChainVerificationEndpointTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            tenant = Tenant(name="Chain Verify Tenant")
            db.add(tenant)
            db.flush()
            admin = User(
                tenant_id=tenant.id,
                username="chain.admin",
                display_name="Chain Admin",
                password_hash="unused",
                role="SECURITY_ADMIN",
            )
            db.add(admin)
            db.commit()
            self.tenant_id = tenant.id
            self.admin_id = admin.id

    def tearDown(self):
        self.engine.dispose()

    def _admin(self):
        with self.Session() as db:
            return db.get(User, self.admin_id)

    def test_untouched_chain_is_reported_valid(self):
        with self.Session() as db:
            for i in range(3):
                append_audit_entry(db, tenant_id=self.tenant_id, event_type="STEP", payload={"i": i})
            db.commit()

        with patch("app.api.operations.get_session_factory", return_value=self.Session):
            response = verify_audit_chain(self._admin())

        self.assertTrue(response.valid)
        self.assertEqual(response.checkedCount, 3)
        self.assertIsNone(response.brokenAtSequence)

    def test_tampered_row_is_reported_broken(self):
        with self.Session() as db:
            for i in range(3):
                append_audit_entry(db, tenant_id=self.tenant_id, event_type="STEP", payload={"i": i})
            db.commit()

        # Directly tamper with a stored row, bypassing append_audit_entry.
        with self.Session() as db:
            second = db.query(AuditLogEntry).filter_by(sequence=2).one()
            second.payload = {"i": "tampered"}
            db.commit()

        with patch("app.api.operations.get_session_factory", return_value=self.Session):
            response = verify_audit_chain(self._admin())

        self.assertFalse(response.valid)
        self.assertEqual(response.brokenAtSequence, 2)


if __name__ == "__main__":
    unittest.main()

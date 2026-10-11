import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auto_confirm import auto_confirm_decision_reason, maybe_auto_confirm
from app.db import Base
from app.models import (
    AuditLogEntry,
    ClassificationDecision,
    ClassificationRecommendation,
    Document,
    DocumentScan,
    SecurityFinding,
    Tenant,
    User,
)
from app.policy import PolicyConfiguration, default_policy_configuration


def _policy(**approval):
    base = default_policy_configuration()
    merged = {**base.approval_policy, **approval}
    return PolicyConfiguration(
        version=base.version, cso_rules=base.cso_rules, approval_policy=merged, model_allowlist=base.model_allowlist
    )


def _rec(grade="O", confidence=0.99, model="klue-roberta-base-model_out"):
    return ClassificationRecommendation(
        id=1, tenant_id=1, document_id=1, recommended_grade=grade, confidence=confidence,
        reason="r", model_version=model, status="PROVISIONAL",
    )


class ReasonTests(unittest.TestCase):
    def test_off_by_default(self):
        self.assertEqual(auto_confirm_decision_reason(approval_policy={}, recommendation=_rec(), finding_count=0), "정책이 꺼져 있음")

    def test_all_conditions_met(self):
        on = {"o_grade_auto_confirm": True}
        self.assertIsNone(auto_confirm_decision_reason(approval_policy=on, recommendation=_rec(), finding_count=0))

    def test_each_condition_blocks(self):
        on = {"o_grade_auto_confirm": True}
        for rec, count in (
            (_rec("S"), 0), (_rec("C"), 0), (_rec(None), 0),
            (_rec(confidence=0.90), 0), (_rec(confidence=None), 0),
            (_rec(), 1),
            (_rec(model="local-rules-placeholder-v0"), 0),
        ):
            self.assertIsNotNone(
                auto_confirm_decision_reason(approval_policy=on, recommendation=rec, finding_count=count),
                (rec.recommended_grade, rec.confidence, rec.model_version, count),
            )

    def test_threshold_is_configurable(self):
        policy = {"o_grade_auto_confirm": True, "o_auto_confirm_min_confidence": 0.8}
        self.assertIsNone(auto_confirm_decision_reason(approval_policy=policy, recommendation=_rec(confidence=0.85), finding_count=0))


class _DbCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def tearDown(self):
        self.engine.dispose()

    def _seed_document(self, *, grade="O", confidence=0.99, findings=0, status="READY_FOR_CLASSIFICATION", uploaded_by=999):
        with self.Session() as db:
            tenant = db.scalar(select(Tenant))
            if tenant is None:
                tenant = Tenant(name="T")
                db.add(tenant)
                db.flush()
            document = Document(
                tenant_id=tenant.id, uploaded_by=uploaded_by, original_filename="d.txt", storage_key="d.txt",
                extension=".txt", mime_type="text/plain", size_bytes=10, sha256="a" * 64, status=status,
            )
            db.add(document)
            db.flush()
            scan = DocumentScan(tenant_id=tenant.id, document_id=document.id, status="READY_FOR_CLASSIFICATION",
                                total_findings=findings, high_severity_count=0, scanner_version="t")
            db.add(scan)
            db.flush()
            for i in range(findings):
                db.add(SecurityFinding(scan_id=scan.id, tenant_id=tenant.id, document_id=document.id,
                                       category="PHONE", severity="LOW", match_count=1, evidence_hash=str(i) * 64))
            rec = ClassificationRecommendation(tenant_id=tenant.id, document_id=document.id, recommended_grade=grade,
                                               confidence=confidence, reason="r", model_version="klue-roberta-base-model_out",
                                               status="PROVISIONAL")
            db.add(rec)
            db.commit()
            return document.id, scan.id, rec.id, tenant.id


class AutoConfirmTests(_DbCase):
    def _run(self, document_id, scan_id, rec_id, policy):
        with self.Session() as db:
            document = db.get(Document, document_id)
            rec = db.get(ClassificationRecommendation, rec_id)
            with patch("app.auto_confirm.get_active_policy_configuration", return_value=policy):
                done = maybe_auto_confirm(db, document, rec, scan_id)
            db.commit()
            return done

    def test_policy_off_does_nothing(self):
        d, s, r, _ = self._seed_document()
        self.assertFalse(self._run(d, s, r, _policy()))
        with self.Session() as db:
            self.assertIsNone(db.scalar(select(ClassificationDecision)))
            self.assertEqual(db.get(Document, d).status, "READY_FOR_CLASSIFICATION")

    def test_policy_on_confirms_clean_o_and_audits_it_as_automatic(self):
        d, s, r, _tenant = self._seed_document()
        self.assertTrue(self._run(d, s, r, _policy(o_grade_auto_confirm=True)))
        with self.Session() as db:
            decision = db.scalar(select(ClassificationDecision))
            self.assertEqual(decision.confirmed_grade, "O")
            self.assertIn("자동 확정", decision.comment)
            system_user = db.get(User, decision.user_id)
            self.assertEqual((system_user.status, system_user.role, system_user.password_hash), ("DISABLED", "SYSTEM", ""))
            self.assertEqual(db.get(Document, d).status, "CLASSIFICATION_CONFIRMED")
            events = [row.event_type for row in db.scalars(select(AuditLogEntry))]
            self.assertIn("CLASSIFICATION_AUTO_CONFIRMED", events)

    def test_risky_documents_are_left_for_a_human(self):
        on = _policy(o_grade_auto_confirm=True)
        for kwargs in ({"grade": "S"}, {"grade": "C"}, {"confidence": 0.5}, {"findings": 1}):
            with self.subTest(**kwargs):
                self.setUp()
                d, s, r, _ = self._seed_document(**kwargs)
                self.assertFalse(self._run(d, s, r, on))
                with self.Session() as db:
                    self.assertIsNone(db.scalar(select(ClassificationDecision)))

    def test_does_not_overwrite_an_existing_human_decision(self):
        d, s, r, tenant_id = self._seed_document()
        with self.Session() as db:
            db.add(ClassificationDecision(tenant_id=tenant_id, document_id=d, user_id=1, recommendation_id=r, confirmed_grade="S"))
            db.commit()
        self.assertFalse(self._run(d, s, r, _policy(o_grade_auto_confirm=True)))


class BulkConfirmTests(_DbCase):
    def _operator(self, tenant_id, role="OPERATOR"):
        with self.Session() as db:
            user = User(tenant_id=tenant_id, username=f"op{role}", display_name="Op", password_hash="x", role=role)
            db.add(user)
            db.commit()
            db.refresh(user)
            return user

    def _call(self, user, ids):
        from app.api.classifications import BulkConfirmRequest, bulk_confirm_classification

        with patch("app.api.classifications.get_session_factory", return_value=self.Session):
            return bulk_confirm_classification(BulkConfirmRequest(document_ids=ids), user)

    def test_confirms_exactly_the_recommended_grade(self):
        a = self._seed_document(grade="O")
        b = self._seed_document(grade="S")
        user = self._operator(a[3])
        result = self._call(user, [a[0], b[0]])
        self.assertEqual((result.confirmed, result.skipped), (2, 0))
        with self.Session() as db:
            grades = {row.document_id: row.confirmed_grade for row in db.scalars(select(ClassificationDecision))}
            self.assertEqual(grades, {a[0]: "O", b[0]: "S"})
            self.assertEqual(db.get(Document, a[0]).status, "CLASSIFICATION_CONFIRMED")

    def test_skips_own_documents_wrong_state_and_unknown_ids(self):
        mine = self._seed_document()
        wrong_state = self._seed_document(status="REJECTED")
        user = self._operator(mine[3])
        with self.Session() as db:
            db.get(Document, mine[0]).uploaded_by = user.id
            db.commit()
        result = self._call(user, [mine[0], wrong_state[0], 424242])
        self.assertEqual((result.confirmed, result.skipped), (0, 3))
        self.assertTrue(all(item.result == "SKIPPED" for item in result.items))

    def test_duplicate_ids_are_confirmed_once(self):
        a = self._seed_document()
        user = self._operator(a[3])
        result = self._call(user, [a[0], a[0], a[0]])
        self.assertEqual(len(result.items), 1)

    def test_plain_user_cannot_use_it(self):
        from app.api.auth import require_roles

        a = self._seed_document()
        user = self._operator(a[3], role="USER")
        with self.assertRaises(HTTPException) as caught:
            require_roles("OPERATOR", "SECURITY_ADMIN", "ADMIN")(current_user=user)
        self.assertEqual(caught.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()

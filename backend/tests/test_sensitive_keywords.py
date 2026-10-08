import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.sensitive_keywords import KeywordCreatePayload, KeywordUpdatePayload, create_keyword, list_keywords, update_keyword
from app.db import Base
from app.masking import mask_text
from app.models import AuditLogEntry, Tenant, User
from app.security_scan import KEYWORD_CATEGORY, keyword_pattern, keyword_rules, scan_text
from app.sensitive_keywords import load_tenant_keywords


class KeywordMatchingTests(unittest.TestCase):
    def _categories(self, text, keywords):
        return {f.category for f in scan_text(text, extra_rules=keyword_rules(keywords))}

    def test_registered_codename_is_detected(self):
        self.assertIn(KEYWORD_CATEGORY, self._categories("다음 주 블루문 프로젝트 일정 공유", [("블루문", "HIGH")]))

    def test_matching_ignores_case_and_spacing(self):
        self.assertIn(KEYWORD_CATEGORY, self._categories("Project bluemoon kickoff", [("BlueMoon", "HIGH")]))
        self.assertIn(KEYWORD_CATEGORY, self._categories("블루문 작전", [("블루 문", "HIGH")]))

    def test_spacing_inside_the_text_cannot_bypass_detection(self):
        self.assertIn(KEYWORD_CATEGORY, self._categories("블 루 문 사업 착수", [("블루문", "MEDIUM")]))
        self.assertIn(KEYWORD_CATEGORY, self._categories("blue moon launch", [("BlueMoon", "MEDIUM")]))

    def test_unrelated_text_is_not_flagged(self):
        self.assertNotIn(KEYWORD_CATEGORY, self._categories("오늘 점심 메뉴 공지", [("블루문", "HIGH")]))

    def test_regex_metacharacters_in_keyword_are_literal(self):
        self.assertNotIn(KEYWORD_CATEGORY, self._categories("abcd", [("a.c", "HIGH")]))
        self.assertIn(KEYWORD_CATEGORY, self._categories("코드 a.c 확인", [("a.c", "HIGH")]))

    def test_keyword_is_masked_before_leaving(self):
        result = mask_text("블루문 예산은 3억", (keyword_pattern("블루문"),))
        self.assertNotIn("블루문", result.masked_text)
        self.assertIn(f"[MASKED:{KEYWORD_CATEGORY}]", result.masked_text)


class KeywordAdminApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)
        with self.Session() as db:
            tenant = Tenant(name="T")
            db.add(tenant); db.flush()
            self.admin = User(tenant_id=tenant.id, username="adm", display_name="A", password_hash="x", role="SECURITY_ADMIN")
            db.add(self.admin); db.commit()
        self.patcher = patch("app.api.sensitive_keywords.get_session_factory", return_value=self.Session)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.engine.dispose()

    def test_created_keyword_is_used_by_the_scanner(self):
        create_keyword(KeywordCreatePayload(keyword="  블루문  ", label="신규 사업"), self.admin)
        with self.Session() as db:
            keywords = load_tenant_keywords(db, self.admin.tenant_id)
        self.assertTrue(any(f.category == KEYWORD_CATEGORY for f in scan_text("블루문 일정", extra_rules=keywords.rules)))

    def test_duplicate_keyword_is_rejected(self):
        create_keyword(KeywordCreatePayload(keyword="블루문"), self.admin)
        with self.assertRaises(HTTPException) as ctx:
            create_keyword(KeywordCreatePayload(keyword="블루문"), self.admin)
        self.assertEqual(ctx.exception.status_code, 409)

    def test_disabled_keyword_stops_matching(self):
        row = create_keyword(KeywordCreatePayload(keyword="블루문"), self.admin)
        update_keyword(row.id, KeywordUpdatePayload(enabled=False), self.admin)
        with self.Session() as db:
            self.assertEqual(load_tenant_keywords(db, self.admin.tenant_id).rules, ())

    def test_audit_log_never_stores_keyword_plaintext(self):
        create_keyword(KeywordCreatePayload(keyword="블루문", label="신규 사업"), self.admin)
        with self.Session() as db:
            entries = db.scalars(select(AuditLogEntry)).all()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].event_type, "SENSITIVE_KEYWORD_CREATED")
        self.assertNotIn("블루문", json.dumps(entries[0].payload, ensure_ascii=False))
        self.assertIn("keyword_sha256", entries[0].payload)

    def test_list_returns_tenant_keywords(self):
        create_keyword(KeywordCreatePayload(keyword="블루문"), self.admin)
        self.assertEqual([k.keyword for k in list_keywords(self.admin)], ["블루문"])


if __name__ == "__main__":
    unittest.main()


class ResponseKeywordTests(unittest.TestCase):
    def test_codename_in_ai_answer_is_blocked_by_post_inspection(self):
        from app.post_inspector import inspect_response

        rules = keyword_rules([("블루문", "MEDIUM")])
        self.assertEqual(inspect_response("답변: 블루문 일정은 다음 달입니다.", rules).status, "BLOCKED")
        self.assertEqual(inspect_response("답변: 일정은 다음 달입니다.", rules).status, "PASSED")
        self.assertEqual(inspect_response("답변: 블루문 일정은 다음 달입니다.").status, "PASSED")


class ChatRateLimitTests(unittest.TestCase):
    def test_user_is_throttled_after_the_window_budget(self):
        from app.api.chat import CHAT_RATE_LIMIT, _enforce_chat_rate_limit
        from app.models import ChatRequest

        engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine, expire_on_commit=False)
        with Session() as db:
            tenant = Tenant(name="T"); db.add(tenant); db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role="USER"); db.add(user); db.flush()
            for _ in range(CHAT_RATE_LIMIT - 1):
                db.add(ChatRequest(tenant_id=tenant.id, user_id=user.id, model="m", policy_version="v", prompt_hash="h" * 64))
            db.commit()
            _enforce_chat_rate_limit(db, user)
            db.add(ChatRequest(tenant_id=tenant.id, user_id=user.id, model="m", policy_version="v", prompt_hash="h" * 64)); db.commit()
            with self.assertRaises(HTTPException) as ctx:
                _enforce_chat_rate_limit(db, user)
            self.assertEqual(ctx.exception.status_code, 429)
        engine.dispose()

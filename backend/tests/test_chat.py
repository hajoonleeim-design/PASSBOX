import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.chat import _parse_request_id, _process_chat, _to_response
from app.db import Base
from app.models import ChatRequest, Tenant, User


class FakeGateway:
    def __init__(self, content="안전한 테스트 응답"):
        self.content = content
        self.calls = 0

    def send(self, **_kwargs):
        self.calls += 1
        return type("GatewayResponse", (), {"content": self.content})()


class ChatFlowTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            tenant = Tenant(name="채팅 테스트 기관")
            db.add(tenant)
            db.flush()
            db.add(
                User(
                    tenant_id=tenant.id,
                    username="chat.user",
                    display_name="Chat User",
                    password_hash="unused",
                    role="USER",
                )
            )
            db.commit()
            self.tenant_id = tenant.id
            self.user_id = 1

    def tearDown(self):
        self.engine.dispose()

    def _new_chat(self, prompt):
        chat = ChatRequest(
            tenant_id=self.tenant_id,
            user_id=self.user_id,
            provider="openai",
            model="gpt-4o-mini",
            policy_version="LOCAL-TEMPLATE-v1",
            prompt_hash="hash",
            prompt_text=prompt,
            payload_status="VALIDATING",
            response_status="NOT_RECEIVED",
            decision_status="UNKNOWN",
            post_inspection_status="PENDING",
        )
        return chat

    def test_allowed_prompt_is_verified_and_raw_prompt_is_cleared(self):
        gateway = FakeGateway()
        with self.Session() as db:
            chat = self._new_chat("이 문서를 한 문장으로 요약해줘.")
            db.add(chat)
            db.flush()
            with patch("app.api.chat.gateway", gateway):
                _process_chat(db, chat, chat.prompt_text)

            self.assertEqual(gateway.calls, 1)
            self.assertEqual(chat.response_status, "VERIFIED")
            self.assertEqual(chat.post_inspection_status, "VERIFIED")
            self.assertEqual(chat.response_text, "안전한 테스트 응답")
            self.assertIsNone(chat.prompt_text)
            self.assertEqual(_to_response(chat).content, "안전한 테스트 응답")

    def test_prompt_with_secret_is_blocked_before_gateway(self):
        gateway = FakeGateway()
        with self.Session() as db:
            chat = self._new_chat("password: not-a-real-secret-1234")
            db.add(chat)
            db.flush()
            with patch("app.api.chat.gateway", gateway):
                _process_chat(db, chat, chat.prompt_text)

            self.assertEqual(gateway.calls, 0)
            self.assertEqual(chat.payload_status, "BLOCKED")
            self.assertEqual(chat.response_status, "BLOCKED")
            self.assertEqual(chat.decision_status, "BLOCKED")
            self.assertIsNone(_to_response(chat).content)
            self.assertIsNone(chat.prompt_text)

    def test_response_content_is_withheld_until_post_inspection_verifies(self):
        with self.Session() as db:
            chat = self._new_chat("질문")
            db.add(chat)
            db.flush()
            chat.response_status = "BLOCKED"
            chat.post_inspection_status = "BLOCKED"
            chat.response_text = "절대 사용자에게 노출되면 안 되는 원문"
            db.commit()
            self.assertIsNone(_to_response(chat).content)

    def test_request_id_parser_accepts_chat_prefix(self):
        self.assertEqual(_parse_request_id("CHAT-42"), 42)
        self.assertEqual(_parse_request_id("42"), 42)


if __name__ == "__main__":
    unittest.main()

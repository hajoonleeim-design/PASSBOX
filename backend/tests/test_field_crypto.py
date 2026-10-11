import unittest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.field_crypto import PREFIX, decrypt_text, encrypt_text
from app.models import ChatRequest, Document, DocumentText, Tenant, User


class FieldEncryptionTests(unittest.TestCase):
    """Readable document and chat text must not sit in the database as plaintext."""

    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        with self.Session() as db:
            tenant = Tenant(name="T"); db.add(tenant); db.flush()
            user = User(tenant_id=tenant.id, username="u", display_name="U", password_hash="x", role="USER"); db.add(user); db.flush()
            doc = Document(tenant_id=tenant.id, uploaded_by=user.id, original_filename="f.txt", storage_key="k", extension=".txt", mime_type="text/plain", size_bytes=1, sha256="a" * 64, status="READY_FOR_CLASSIFICATION")
            db.add(doc); db.flush()
            db.add(DocumentText(tenant_id=tenant.id, document_id=doc.id, extracted_text="주민번호 900101-1234567", char_count=10, status="EXTRACTED", extractor="test"))
            db.add(ChatRequest(tenant_id=tenant.id, user_id=user.id, provider="gemini", model="m", policy_version="v", prompt_hash="h",
                               prompt_text="연락처는 010-1234-5678", response_text="답변 본문"))
            db.commit()

    def tearDown(self):
        self.engine.dispose()

    def test_stored_values_are_ciphertext(self):
        with self.engine.connect() as conn:
            stored = conn.execute(text("select extracted_text from document_texts")).scalar()
            prompt, answer = conn.execute(text("select prompt_text, response_text from chat_requests")).one()
        for value in (stored, prompt, answer):
            self.assertTrue(value.startswith(PREFIX), value[:20])
        self.assertNotIn("900101", stored)
        self.assertNotIn("010-1234", prompt)

    def test_values_read_back_as_plaintext(self):
        with self.Session() as db:
            self.assertEqual(db.query(DocumentText).one().extracted_text, "주민번호 900101-1234567")
            self.assertEqual(db.query(ChatRequest).one().prompt_text, "연락처는 010-1234-5678")

    def test_same_text_encrypts_differently_each_time(self):
        self.assertNotEqual(encrypt_text("같은 문장"), encrypt_text("같은 문장"))

    def test_tampered_ciphertext_does_not_decrypt(self):
        token = encrypt_text("원문")
        tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
        with self.assertRaises(Exception):
            decrypt_text(tampered)

    def test_legacy_plaintext_rows_are_still_readable(self):
        with self.engine.begin() as conn:
            conn.execute(text("update chat_requests set response_text = '예전 평문 답변'"))
        with self.Session() as db:
            self.assertEqual(db.query(ChatRequest).one().response_text, "예전 평문 답변")


if __name__ == "__main__":
    unittest.main()

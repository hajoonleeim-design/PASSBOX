"""기존에 평문으로 저장된 추출 본문·승인 마스킹본·대화 기록을 한 번에 암호화한다.

여러 번 실행해도 안전하다(이미 암호화된 값은 건드리지 않음).
    python migrate_encrypt_text.py          # 미리보기
    python migrate_encrypt_text.py --apply  # 실제 변환
"""
import sys

from sqlalchemy import text

from app.db import get_session_factory
from app.field_crypto import encrypt_text, is_encrypted

COLUMNS = [("document_texts", "extracted_text"), ("outbound_approvals", "masked_payload"),
           ("chat_requests", "prompt_text"), ("chat_requests", "response_text")]


def main(apply: bool) -> None:
    with get_session_factory()() as db:
        for table, column in COLUMNS:
            rows = db.execute(text(f"select id, {column} from {table} where {column} is not null")).all()
            todo = [(rid, val) for rid, val in rows if not is_encrypted(val)]
            print(f"{table}.{column}: {len(rows)}건 중 평문 {len(todo)}건")
            if apply:
                for rid, val in todo:
                    db.execute(text(f"update {table} set {column} = :v where id = :i"), {"v": encrypt_text(val), "i": rid})
        if apply:
            db.commit()
            print("암호화 완료")


if __name__ == "__main__":
    main("--apply" in sys.argv)

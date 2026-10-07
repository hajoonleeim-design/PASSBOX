from dataclasses import dataclass

from sqlalchemy import select

from app.models import SensitiveKeyword
from app.security_scan import _Rule, keyword_pattern, keyword_rules


@dataclass(frozen=True)
class TenantKeywords:
    rules: tuple[_Rule, ...]
    mask_patterns: tuple[str, ...]


def load_tenant_keywords(db, tenant_id: int) -> TenantKeywords:
    rows = db.execute(
        select(SensitiveKeyword.keyword, SensitiveKeyword.severity).where(
            SensitiveKeyword.tenant_id == tenant_id,
            SensitiveKeyword.enabled.is_(True),
        )
    ).all()
    pairs = [(keyword, severity) for keyword, severity in rows]
    return TenantKeywords(
        rules=keyword_rules(pairs),
        mask_patterns=tuple(keyword_pattern(keyword) for keyword, _ in pairs if keyword.strip()),
    )

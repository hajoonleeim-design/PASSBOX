from dataclasses import dataclass

from app.security_scan import Finding, _Rule, scan_response_links, scan_text


@dataclass(frozen=True)
class PostInspectionResult:
    status: str
    categories: list[str]
    findings: list[Finding]


def inspect_response(text: str, extra_rules: tuple[_Rule, ...] = ()) -> PostInspectionResult:
    findings = scan_text(text, extra_rules=extra_rules) + scan_response_links(text)
    categories = sorted({finding.category for finding in findings})
    return PostInspectionResult(
        status="BLOCKED" if findings else "PASSED",
        categories=categories,
        findings=findings,
    )

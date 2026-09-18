from dataclasses import dataclass

from app.security_scan import Finding, scan_text


@dataclass(frozen=True)
class PostInspectionResult:
    status: str
    categories: list[str]
    findings: list[Finding]


def inspect_response(text: str) -> PostInspectionResult:
    findings = scan_text(text)
    categories = sorted({finding.category for finding in findings})
    return PostInspectionResult(
        status="BLOCKED" if findings else "PASSED",
        categories=categories,
        findings=findings,
    )

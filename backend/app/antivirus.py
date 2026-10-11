"""Malware scanning of quarantined uploads through a ClamAV daemon (clamd).

The file is streamed to clamd with the INSTREAM command over TCP, so PASSBOX never
needs the ClamAV binaries on the API host and clamd can run on a separate inspection
server (or a container next to the API).

CLAMAV_MODE controls what happens when clamd cannot be reached:
  off       - not used; only the built-in EICAR self-test signature check runs
  optional  - scan when available, log and continue when clamd is down (development)
  required  - fail closed: an upload that cannot be scanned is rejected (production default)
"""
import io
import logging
import socket
import struct
from dataclasses import dataclass
from pathlib import Path

from app.db import Settings

_log = logging.getLogger("passbox.antivirus")
_CHUNK = 64 * 1024


@dataclass(frozen=True)
class ScanResult:
    status: str  # CLEAN | INFECTED | UNAVAILABLE | SKIPPED
    signature: str | None = None
    engine: str = "clamav"


class AntivirusUnavailable(RuntimeError):
    pass


def _mode(settings: Settings) -> str:
    mode = settings.clamav_mode.strip().lower()
    return mode if mode in {"off", "optional", "required"} else "required"


def _instream(source, host: str, port: int, timeout: float) -> str:
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(b"zINSTREAM\0")
        while chunk := source.read(_CHUNK):
            sock.sendall(struct.pack("!L", len(chunk)) + chunk)
        sock.sendall(struct.pack("!L", 0))
        reply = b""
        while not reply.endswith(b"\0"):
            part = sock.recv(4096)
            if not part:
                break
            reply += part
    return reply.rstrip(b"\0").decode("utf-8", "replace")


def scan_file(path: Path, settings: Settings | None = None) -> ScanResult:
    with path.open("rb") as source:
        return _scan(source, settings or Settings())


def scan_bytes(data: bytes, settings: Settings | None = None) -> ScanResult:
    return _scan(io.BytesIO(data), settings or Settings())


def _scan(source, settings: Settings) -> ScanResult:
    mode = _mode(settings)
    if mode == "off":
        return ScanResult(status="SKIPPED")
    try:
        reply = _instream(source, settings.clamav_host, settings.clamav_port, settings.clamav_timeout_seconds)
    except OSError as exc:
        _log.warning("clamd unreachable at %s:%s (%s)", settings.clamav_host, settings.clamav_port, exc)
        if mode == "required":
            raise AntivirusUnavailable("악성코드 검사 서버(ClamAV)에 연결할 수 없습니다.") from exc
        return ScanResult(status="UNAVAILABLE")
    # "stream: OK" | "stream: Eicar-Test-Signature FOUND" | "INSTREAM size limit exceeded. ERROR"
    if reply.endswith("FOUND"):
        return ScanResult(status="INFECTED", signature=reply.split(":", 1)[-1].rsplit(" ", 1)[0].strip())
    if reply.endswith("OK"):
        return ScanResult(status="CLEAN")
    _log.warning("clamd error reply: %s", reply)
    if mode == "required":
        raise AntivirusUnavailable(f"악성코드 검사에 실패했습니다: {reply}")
    return ScanResult(status="UNAVAILABLE")
